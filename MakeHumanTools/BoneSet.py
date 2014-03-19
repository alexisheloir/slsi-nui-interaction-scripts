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

MH_ARM_CONTROLLERS = [
                      "Wrist_R",
                      "Wrist_L",
                      "ElbowPT_R",
                      "ElbowPT_L"
                      ]

# 20 Facial control rigs. Listed from top to bottom (arbitrary decision)
# Don't change the order.
MH_FACIAL_CONTROLLERS = [
                         "PBrows",   # 0
                         "PBrow_R",
                         "PBrow_L",
                         "PUpLid_R",
                         "PUpLid_L",
                         "PLoLid_L",
                         "PLoLid_R",
                         
                         "PNose",    # 7
                         "PCheek_L",
                         "PCheek_R",
                         
                         "PUpLipMid",    # 10
                         "PUpLip_R",
                         "PUpLip_L",
                         "PMouth_R",     # 13
                         "PMouth_L",     # 14
                         "PLoLip_R",
                         "PLoLip_L",
                         "PLoLipMid",    # 17
                         
                         "PMouthMid",    # 18
                         "PJaw"
                         ]

MH_EXTRA_CONTROLLERS = [
                        "Jaw",
                        "Neck",
                        "Gaze"
                        ]

MH_BODY_CONTROLLERS = [
                       "LegIK_R",
                       "LegIK_L",
                       "KneePT_R",
                       "KneePT_L",
                       "Root",
                       "Shoulders"
                       ]



L_HAND_BONES = [
                "Finger-1-1_L", "Finger-1-2_L", "Finger-1-3_L",
                "Finger-2-1_L", "Finger-2-2_L", "Finger-2-3_L",
                "Finger-3-1_L", "Finger-3-2_L", "Finger-3-3_L",
                "Finger-4-1_L", "Finger-4-2_L", "Finger-4-3_L",
                "Finger-5-1_L", "Finger-5-2_L", "Finger-5-3_L",
                "Palm-1_L", "Palm-2_L", "Palm-3_L", "Palm-4_L", "Palm-5_L",
                "Wrist-1_L", "Wrist-2_L"
                ]

R_HAND_BONES = [
                "Finger-1-1_R", "Finger-1-2_R", "Finger-1-3_R",
                "Finger-2-1_R", "Finger-2-2_R", "Finger-2-3_R",
                "Finger-3-1_R", "Finger-3-2_R", "Finger-3-3_R",
                "Finger-4-1_R", "Finger-4-2_R", "Finger-4-3_R",
                "Finger-5-1_R", "Finger-5-2_R", "Finger-5-3_R",
                "Palm-1_R", "Palm-2_R", "Palm-3_R", "Palm-4_R", "Palm-5_R",
                "Wrist-1_R", "Wrist-2_R"
                ]
