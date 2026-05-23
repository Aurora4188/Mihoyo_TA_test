import json
import maya.cmds as cm

import os
import userSetup

import maya.api.OpenMaya as om

def short_name(obj):
    return obj.split("|")[-1]

def duplicateJointChain(joints=None, name=""):
    copyJoint = cm.duplicate(joints[0], rc=True)
    jointChain = []
    # for i, j in zip(copyJoint, joints):
    #     renameJoint = cm.rename(i, j + name)
    #     jointChain.append(renameJoint)

    for dup, src in zip(copyJoint, joints):
        renameJoint = cm.rename(dup, short_name(src) + name)
        jointChain.append(renameJoint)

    return jointChain


def ctrlGenerator(target=None, name="", r=5, addLink=False):
    ctrl = cm.circle(name=name + "_ctrl", radius=r)[0]
    ctrlDrv = cm.group(ctrl, name=ctrl + "_drv")
    ctrlOffset = cm.group(ctrlDrv, name=ctrl + "_offset")

    cm.matchTransform(ctrlOffset, target)

    if addLink:
        cm.parentConstraint(ctrl, target)

    return [ctrlOffset, ctrl, ctrlDrv]


def ikfkGenerator(name=""):
    sel = cm.ls(selection=True)
    ##for selection error
    if len(sel) != 3:
        cm.error("Please select a 3-joint chain: start, mid, end.")

    result_chain = sel

    fkChain = duplicateJointChain(joints=sel, name="_fk")
    ikChain = duplicateJointChain(joints=sel, name="_ik")

    constraints = []

    for result_jnt, ik_jnt, fk_jnt in zip(result_chain, ikChain, fkChain):
        nexConstraint = cm.parentConstraint(ik_jnt, fk_jnt, result_jnt, mo=True)[0]
        constraints.append(nexConstraint)

    ctrlOffsets = []
    fkCtrls = []
    for i in fkChain:

        ctrl = ctrlGenerator(target=i, name=i + "_fk", addLink=True)
        ctrlOffsets.append(ctrl[0])
        fkCtrls.append(ctrl[1])

    # 把offset和ctrl list的顺序反过来便于parent fk ctrl chain
    # ctrlOffsets = ctrlOffsets[::-1]
    # fkCtrls = fkCtrls[::-1]

    # 保留一份 start-mid-end 顺序 for align/reset/stretch
    fkCtrls_ordered = fkCtrls[:]
    ctrlOffsets_ordered = ctrlOffsets[:]

    # for parent - reversed
    reverseOffsets = ctrlOffsets[::-1]
    reverseCtrls = fkCtrls[::-1]

    # for i, j in enumerate(ctrlOffsets):
    #     if i < len(ctrlOffsets) - 1:
    #         cm.parent(j, fkCtrls[i + 1])
    for i, offset in enumerate(reverseOffsets):
        if i < len(reverseOffsets) - 1:
            cm.parent(offset, reverseCtrls[i + 1])

    fkGrp = cm.group(ctrlOffsets_ordered[0], name=name + "_fk_grp")
    # fkGrp = cm.group(ctrlOffsets[-1], name=name + "_fk_grp")

    newIkHandle = cm.ikHandle(name=name + "_ikHandle", startJoint=ikChain[0],
                              endEffector=ikChain[-1], solver="ikRPsolver")[0]
    ikCtrl = ctrlGenerator(target=newIkHandle, name=name + "_ik", addLink=True)

    # addLink default 是false
    poleCtrl = ctrlGenerator(target=ikChain[1], name=name + "_pole_ctrl")

    cm.setAttr(poleCtrl[-1] + ".ty", -20)
    cm.poleVectorConstraint(poleCtrl[1], newIkHandle)
    ikGrp = cm.group(ikCtrl[0], poleCtrl[0], name=name + "_ik_grp")

    switchCtrl = ctrlGenerator(target=sel[-1], name=name + "_switch")
    cm.addAttr(switchCtrl[1], longName="ikfk", at="float", min=0, max=10, dv=0, keyable=True)

    # 在node graph里创建setrange和reverse
    SRNode = cm.createNode("setRange", name=switchCtrl[1] + "_sr")
    RVNode = cm.createNode("reverse", name=switchCtrl[1] + "_rv")

    # switch ctrl的ikfk attr连接到setrange setRange连接到reverse
    cm.connectAttr(switchCtrl[1] + ".ikfk", SRNode + ".valueX")
    cm.connectAttr(SRNode + ".outValueX", RVNode + ".inputX")

    cm.setAttr(SRNode + ".maxX", 1)
    cm.setAttr(SRNode + ".oldMaxX", 10)

    # may cause same name issue
    # for constraint, ikJoint, fkJoint in zip(constraints, ikChain, fkChain):
    #     cm.connectAttr(RVNode + ".outputX", f"{constraint}.{ikJoint}W0", force=True)
    #     cm.connectAttr(SRNode + ".outValueX", f"{constraint}.{fkJoint}W1", force=True)

    for constraint in constraints:
        aliases = cm.parentConstraint(constraint, q=True, weightAliasList=True)

        cm.connectAttr(RVNode + ".outputX", f"{constraint}.{aliases[0]}", force=True)
        cm.connectAttr(SRNode + ".outValueX", f"{constraint}.{aliases[1]}", force=True)

    cm.connectAttr(RVNode + ".outputX", ikGrp + ".v", force=True)
    cm.connectAttr(SRNode + ".outValueX", fkGrp + ".v", force=True)

    cm.pointConstraint(sel[-1], switchCtrl[0], maintainOffset=False)
    cm.select(clear=True)

    rig_data = {
        "name": name,
        "result_chain": result_chain,
        "fk_chain": fkChain,
        "ik_chain": ikChain,
        "fk_ctrls": fkCtrls_ordered,
        "ik_ctrl": ikCtrl[1],
        "pole_ctrl": poleCtrl[1],
        "switch_ctrl": switchCtrl[1],
        "ik_grp": ikGrp,
        "fk_grp": fkGrp,
        "ik_weight": RVNode + ".outputX",
        "fk_weight": SRNode + ".outValueX"
    }

    setup_visibility_controls(rig_data)

    cm.select(clear=True)
    return rig_data

def set_ikfk_value(rig_data, value):
    cm.setAttr(rig_data["switch_ctrl"] + ".ikfk", value)


def match_world_matrix(source, target):
    matrix = cm.xform(source, q=True, ws=True, m=True)
    cm.xform(target, ws=True, m=matrix)

def get_world_pos(obj):
    return om.MVector(cm.xform(obj, q=True, ws=True, t=True))

def get_distance(a, b):
    return (get_world_pos(b) - get_world_pos(a)).length()

def add_float_attr(node, attr, min_value=None, max_value=None, default=1.0):
    if not cm.attributeQuery(attr, node=node, exists=True):
        kwargs = {
            "ln": attr,
            "at": "double",
            "keyable": True,
            "dv": default
        }

        if min_value is not None:
            kwargs["min"] = min_value
        if max_value is not None:
            kwargs["max"] = max_value

        cm.addAttr(node, **kwargs)

    return f"{node}.{attr}"


# ---------------------------
# ikfk Alignment

def compute_pole_vector_position(start_jnt, mid_jnt, end_jnt, distance=20, direction = 1):
    start_pos = get_world_pos(start_jnt)
    mid_pos = get_world_pos(mid_jnt)
    end_pos = get_world_pos(end_jnt)

    start_to_end = end_pos - start_pos
    start_to_mid = mid_pos - start_pos

    # project mid to the start-end direction line
    projection_length = start_to_mid * start_to_end.normal()
    projection_pos = start_pos + start_to_end.normal() * projection_length

    # pole vector dir
    pole_dir = (mid_pos - projection_pos).normal()
    pole_pos = mid_pos + pole_dir * distance * direction

    return [pole_pos.x, pole_pos.y, pole_pos.z]

def ik_align_fk(rig_data, pole_distance=80):
    """
    IK ctrl to FK end joint；
    compute Pole ctrl pos
    """
    fk_chain = rig_data["fk_chain"]
    ik_ctrl = rig_data["ik_ctrl"]
    pole_ctrl = rig_data["pole_ctrl"]

    # match_world_matrix(fk_chain[-1], ik_ctrl)

    pole_pos = compute_pole_vector_position(
        fk_chain[0],
        fk_chain[1],
        fk_chain[2],
        distance=pole_distance,
        direction=1
    )
    print("FK chain:", fk_chain)
    print("Pole pos:", pole_pos)

    cm.xform(pole_ctrl, ws=True, t=pole_pos)
    match_world_matrix(fk_chain[-1], ik_ctrl)

    print("IK Align FK finished.")

def fk_align_ik(rig_data):
    """
    FK controls to IK joint chain pos
    """
    ik_chain = rig_data["ik_chain"]
    fk_ctrls = rig_data["fk_ctrls"]

    for ik_jnt, fk_ctrl in zip(ik_chain, fk_ctrls):
        match_world_matrix(ik_jnt, fk_ctrl)

    print("FK Align IK finished.")

def reset_ctrl(ctrl, reset_translate=True, reset_rotate=True, reset_scale=True):
    if reset_translate:
        for axis in "XYZ":
            attr = f"{ctrl}.translate{axis}"
            if cm.objExists(attr) and not cm.getAttr(attr, lock=True):
                cm.setAttr(attr, 0)

    if reset_rotate:
        for axis in "XYZ":
            attr = f"{ctrl}.rotate{axis}"
            if cm.objExists(attr) and not cm.getAttr(attr, lock=True):
                cm.setAttr(attr, 0)

    if reset_scale:
        for axis in "XYZ":
            attr = f"{ctrl}.scale{axis}"
            if cm.objExists(attr) and not cm.getAttr(attr, lock=True):
                cm.setAttr(attr, 1)


def ik_reset(rig_data):
    reset_ctrl(rig_data["ik_ctrl"])
    reset_ctrl(rig_data["pole_ctrl"])
    print("IK Reset finished.")


def fk_reset(rig_data):
    for ctrl in rig_data["fk_ctrls"]:
        reset_ctrl(
            ctrl,
            reset_translate=False,
            reset_rotate=True,
            reset_scale=True
        )

    print("FK Reset finished.")
# -------------------------
# stretch functions
# -------------------------
def create_distance_locs(start_target, end_target, prefix):
    start_loc = cm.spaceLocator(name=prefix + "_start_dist_loc")[0]
    end_loc = cm.spaceLocator(name=prefix + "_end_dist_loc")[0]

    cm.pointConstraint(start_target, start_loc, mo=False)
    cm.pointConstraint(end_target, end_loc, mo=False)

    return start_loc, end_loc

def create_distance_node(start_loc, end_loc, prefix):
    dist_node = cm.createNode("distanceBetween", name=prefix + "_distanceBetween")

    cm.connectAttr(start_loc + ".worldPosition[0]", dist_node + ".point1", force=True)
    cm.connectAttr(end_loc + ".worldPosition[0]", dist_node + ".point2", force=True)

    return dist_node

def create_ratio_node(distance_attr, original_length, prefix):
    md = cm.createNode("multiplyDivide", name=prefix + "_ratio_md")
    # set it to divide
    cm.setAttr(md + ".operation", 2)
    cm.connectAttr(distance_attr, md + ".input1X", force=True)
    cm.setAttr(md + ".input2X", original_length)

    return md + ".outputX"

def create_limit_conditions(ratio_attr, compress_attr, stretch_attr, prefix):
    compress_cond = cm.createNode("condition", name=prefix + "_compress_condition")
    cm.setAttr(compress_cond + ".operation", 4)  # less than

    cm.connectAttr(ratio_attr, compress_cond + ".firstTerm", force=True)
    cm.connectAttr(compress_attr, compress_cond + ".secondTerm", force=True)

    cm.connectAttr(compress_attr, compress_cond + ".colorIfTrueR", force=True)
    cm.connectAttr(ratio_attr, compress_cond + ".colorIfFalseR", force=True)

    stretch_cond = cm.createNode("condition", name=prefix + "_stretch_condition")
    cm.setAttr(stretch_cond + ".operation", 2)  # greater than

    cm.connectAttr(compress_cond + ".outColorR", stretch_cond + ".firstTerm", force=True)
    cm.connectAttr(stretch_attr, stretch_cond + ".secondTerm", force=True)

    cm.connectAttr(stretch_attr, stretch_cond + ".colorIfTrueR", force=True)
    cm.connectAttr(compress_cond + ".outColorR", stretch_cond + ".colorIfFalseR", force=True)

    return stretch_cond + ".outColorR"

def create_ik_stretch(rig_data, axis="X"):
    name = rig_data["name"]
    ik_chain = rig_data["ik_chain"]
    ik_ctrl = rig_data["ik_ctrl"]

    upper_len = get_distance(ik_chain[0], ik_chain[1])
    lower_len = get_distance(ik_chain[1], ik_chain[2])
    total_len = upper_len + lower_len

    compress_attr = add_float_attr(
        ik_ctrl,
        "compressLimit",
        min_value=0,
        max_value=1,
        default=1
    )

    stretch_attr = add_float_attr(ik_ctrl,"stretchLimit", min_value=1, max_value=3, default=1.5)
    # important: end locator follows IK ctrl, not end joint
    start_loc, end_loc = create_distance_locs(ik_chain[0], ik_ctrl, name + "_ikStretch")

    dist_node = create_distance_node(start_loc, end_loc, name + "_ikStretch")

    ratio_attr = create_ratio_node(dist_node + ".distance", total_len, name + "_ikStretch")

    final_scale_attr = create_limit_conditions(ratio_attr, compress_attr, stretch_attr, name + "_ikStretch")

    ## test
    # print("===== IK STRETCH DEBUG =====")
    # print("IK CHAIN:", ik_chain)
    axis_attr = "scale" + axis.upper()

    # print("CONNECT IK STRETCH TO:")
    # print(ik_chain[0] + "." + axis_attr)
    # print(ik_chain[1] + "." + axis_attr)
    # print("FROM:", final_scale_attr)

    cm.connectAttr(final_scale_attr, ik_chain[0] + "." + axis_attr, force=True)
    cm.connectAttr(final_scale_attr, ik_chain[1] + "." + axis_attr, force=True)

    return final_scale_attr

def create_fk_stretch(rig_data, axis="X"):
    """
    FK stretch:
    给前两个 FK ctrl 添加 stretch 属性。
    upper FK ctrl 控制 upper segment scale；
    mid FK ctrl 控制 lower segment scale。
    """
    fk_ctrls = rig_data["fk_ctrls"]

    upper_fk_scale = add_float_attr(
        fk_ctrls[0],"stretch", min_value=0.01, max_value=3, default=1)

    lower_fk_scale = add_float_attr(fk_ctrls[1], "stretch", min_value=0.01, max_value=3, default=1)

    return upper_fk_scale, lower_fk_scale

def connect_stretch_to_result(rig_data, ik_scale_attr, fk_upper_attr, fk_lower_attr, axis="X"):
    name = rig_data["name"]
    result_chain = rig_data["result_chain"]
    switch_attr = rig_data["switch_ctrl"] + ".ikfk"

    # 因为 ikfk 是 0-10，这里转成 0-1
    sr = cm.createNode("setRange", name=name + "_stretchSwitch_sr")
    cm.connectAttr(switch_attr, sr + ".valueX", force=True)
    cm.setAttr(sr + ".maxX", 1)
    cm.setAttr(sr + ".oldMaxX", 10)

    upper_blend = cm.createNode("blendColors", name=name + "_upper_stretch_blend")
    lower_blend = cm.createNode("blendColors", name=name + "_lower_stretch_blend")

    # ikfk = 0 是 IK，ikfk = 10 是 FK
    # blender = 0 输出 color1
    # blender = 1 输出 color2


    cm.connectAttr(ik_scale_attr, upper_blend + ".color1R", force=True)
    cm.connectAttr(fk_upper_attr, upper_blend + ".color2R", force=True)

    cm.connectAttr(ik_scale_attr, lower_blend + ".color1R", force=True)
    cm.connectAttr(fk_lower_attr, lower_blend + ".color2R", force=True)

    cm.connectAttr(sr + ".outValueX", upper_blend + ".blender", force=True)
    cm.connectAttr(sr + ".outValueX", lower_blend + ".blender", force=True)

    cm.connectAttr(
        upper_blend + ".outputR",
        result_chain[0] + ".scale" + axis.upper(),
        force=True
    )

    cm.connectAttr(
        lower_blend + ".outputR",
        result_chain[1] + ".scale" + axis.upper(),
        force=True
    )

def addStretch(rig_data, axis="X"):
    ik_scale_attr = create_ik_stretch(rig_data, axis=axis)
    fk_upper_attr, fk_lower_attr = create_fk_stretch(rig_data, axis=axis)

    connect_stretch_to_result(
        rig_data,
        ik_scale_attr,
        fk_upper_attr,
        fk_lower_attr,
        axis=axis
    )

    print("Stretch setup finished:", rig_data["name"])


# -------------------------\
# modify visibility
def add_visibility_attrs(switch_ctrl):
    attrs = {
        "auto_vis": 1,
        "ik_vis": 1,
        "fk_vis": 1
    }

    for attr, default in attrs.items():
        if not cm.attributeQuery(attr, node=switch_ctrl, exists=True):
            cm.addAttr(
                switch_ctrl,
                ln=attr,
                at="bool",
                dv=default,
                keyable=True
            )

def setup_visibility_controls(rig_data):
    """
    auto_vis = 1: 根据 ikfk 自动显示隐藏
    auto_vis = 0: 使用 ik_vis / fk_vis 手动控制
    """
    switch_ctrl = rig_data["switch_ctrl"]
    ik_grp = rig_data["ik_grp"]
    fk_grp = rig_data["fk_grp"]

    ik_weight = rig_data["ik_weight"]
    fk_weight = rig_data["fk_weight"]

    add_visibility_attrs(switch_ctrl)

    ik_blend = cm.createNode("blendColors", name=switch_ctrl + "_ikVis_blend")
    fk_blend = cm.createNode("blendColors", name=switch_ctrl + "_fkVis_blend")

    # color1 = auto visibility
    cm.connectAttr(ik_weight, ik_blend + ".color1R", force=True)
    cm.connectAttr(fk_weight, fk_blend + ".color1R", force=True)

    # color2 = manual visibility
    cm.connectAttr(switch_ctrl + ".ik_vis", ik_blend + ".color2R", force=True)
    cm.connectAttr(switch_ctrl + ".fk_vis", fk_blend + ".color2R", force=True)

    # auto_vis 控制 auto / manual
    cm.connectAttr(switch_ctrl + ".auto_vis", ik_blend + ".blender", force=True)
    cm.connectAttr(switch_ctrl + ".auto_vis", fk_blend + ".blender", force=True)

    cm.connectAttr(ik_blend + ".outputR", ik_grp + ".visibility", force=True)
    cm.connectAttr(fk_blend + ".outputR", fk_grp + ".visibility", force=True)

    print("Visibility controls setup finished.")

def set_auto_vis(rig_data, value=True):
    cm.setAttr(rig_data["switch_ctrl"] + ".auto_vis", int(value))


def set_ik_vis(rig_data, value=True):
    cm.setAttr(rig_data["switch_ctrl"] + ".ik_vis", int(value))


def set_fk_vis(rig_data, value=True):
    cm.setAttr(rig_data["switch_ctrl"] + ".fk_vis", int(value))