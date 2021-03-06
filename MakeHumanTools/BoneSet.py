#The Sign Language Synthesis and Interaction Research Tools
#    Copyright (C) 2014  Fabrizio Nunnari, Alexis Heloir, DFKI
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# Set of names used to directly drive MakeHuman skeleton bones.
#


MH_HAND_CONTROLLER_R = "hand.ik.R"
MH_HAND_CONTROLLER_L = "hand.ik.L"
MH_ELBOW_CONTROLLER_base = "elbow.pt.ik"
MH_ELBOW_CONTROLLER_R = MH_ELBOW_CONTROLLER_base+".R"
MH_ELBOW_CONTROLLER_L = MH_ELBOW_CONTROLLER_base+".L"

MH_ARM_CONTROLLERS = [
                      MH_HAND_CONTROLLER_R,
                      MH_HAND_CONTROLLER_L,
                      MH_ELBOW_CONTROLLER_R,
                      MH_ELBOW_CONTROLLER_L
                      ]



# 25 Facial control rigs. Listed from top to bottom, inner to outer, right first.
# Don't change the order! It matters for some applications.
MH_FACIAL_CONTROLLERS = [
                  "p_brow_mid",     # 0
                  "p_brow_in.R",
                  "p_brow_in.L",
                  "p_brow_out.R",
                  "p_brow_out.L",

                  "p_up_lid.R",     #5
                  "p_up_lid.L",
                  "p_lo_lid.R",
                  "p_lo_lid.L",

                  "p_nose",         # 9
                  "p_cheek.R",
                  "p_cheek.L",

                  "p_up_lip_mid",   # 12
                  "p_up_lip.R",
                  "p_up_lip.L",
                  "p_lo_lip_mid",
                  "p_lo_lip.R",
                  "p_lo_lip.L",

                  "p_mouth_mid",    # 18
                  "p_mouth_in.R",
                  "p_mouth_in.L",
                  "p_mouth_out.R",
                  "p_mouth_out.L",

                  "p_tongue",       #23

                  "p_jaw",          #24

                  #"p_face"   # Main box reference for facial pose_bones. Not really affecting expressions.

                  ]

# 4 controllers for the eyelids. Listed from top to bottom, right first.
# Don't change the order! It matters for some applications.
MH_EYELID_CONTROLLERS = [
			"uplid.R",
			"uplid.L",
			"lolid.R",
			"lolid.L",
]



MH_LEG_CONTROLLER_R = "foot.ik.R"
MH_LEG_CONTROLLER_L = "foot.ik.L"
MH_KNEE_CONTROLLER_R = "knee.pt.ik.R"
MH_KNEE_CONTROLLER_L = "knee.pt.ik.L"
MH_LEG_CONTROLLERS = [
                      MH_LEG_CONTROLLER_R,
                      MH_LEG_CONTROLLER_L,
                      MH_KNEE_CONTROLLER_R,
                      MH_KNEE_CONTROLLER_L,
                      ]

MH_CONTROLLER_JAW = "jaw"
MH_CONTROLLER_NECK = "neck"
MH_CONTROLLER_GAZE = "gaze"
MH_HEAD_CONTROLLERS = [
                        MH_CONTROLLER_JAW,
                        MH_CONTROLLER_NECK,
                        MH_CONTROLLER_GAZE
                        ]

MH_ROOT_CONTROLLER = "root"
MH_UPCHEST_CONTROLLER = "chest-1"
MH_HIPS_CONTROLLER = "hips"
MH_BODY_CONTROLLERS = [
                        "spine",
                        "spine-1",
                        "chest",
                        MH_UPCHEST_CONTROLLER,
                        MH_ROOT_CONTROLLER,
                        MH_HIPS_CONTROLLER
                       ]


MH_HAND_CONTROLLERS_R = [ "thumb.R", "index.R", "middle.R", "ring.R", "pinky.R" ]
MH_HAND_CONTROLLERS_L = [  "thumb.L", "index.L", "middle.L", "ring.L", "pinky.L" ]
MH_HAND_CONTROLLERS = MH_HAND_CONTROLLERS_R + MH_HAND_CONTROLLERS_L 


MH_ALL_CONTROLLERS = MH_ARM_CONTROLLERS + MH_FACIAL_CONTROLLERS + MH_LEG_CONTROLLERS + MH_HEAD_CONTROLLERS + MH_BODY_CONTROLLERS + MH_HAND_CONTROLLERS



MH_EU_MOUTH_RETRACTION = "Mhsmouth_retraction"



MH_HAND_BONES_base = [
    "palm_ring",
    "f_ring.01",
    "f_ring.02",
    "f_ring.03",
    "thumb.01",
    "thumb.02",
    "thumb.03",
    "palm_index",
    "f_index.01",
    "f_index.02",
    "f_index.03",
    "palm_middle",
    "f_middle.01",
    "f_middle.02",
    "f_middle.03",
    "palm_pinky",
    "f_pinky.01",
    "f_pinky.02",
    "f_pinky.03",
]


MH_HAND_BONES_R = [ b+".R" for b in MH_HAND_BONES_base]
MH_HAND_BONES_L = [ b+".L" for b in MH_HAND_BONES_base]
MH_HAND_BONES = MH_HAND_BONES_R + MH_HAND_BONES_L

MH_SHOULDER_BONE_base = "upper_arm"
MH_ELBOW_BONE_base = "forearm"
MH_WRIST_BONE_base = "hand"

MH_FOREARM_BONE_base = "forearm"

MH_ALL_BONES = MH_HAND_BONES_R + MH_HAND_BONES_L
