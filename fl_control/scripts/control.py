#!/usr/bin/env python
import sys
from actionlib.simple_action_client import SimpleActionClient
import rospy
from move_goal_builder import MoveItGoalBuilder
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from moveit_msgs.srv import GetPositionIK, GetPositionIKRequest, \
    GetPositionIKResponse
from sensor_msgs.msg import JointState
from moveit_msgs.msg import MoveGroupAction, MoveGroupActionGoal, \
    MoveGroupActionResult, MoveGroupActionFeedback, MoveItErrorCodes

class Quartets:
    def __init__(self, x=0, y=0, z=0, w=1):
        self.x = x
        self.y = y
        self.z = z
        self.w = w


class Coordinates:
    def __init__(self, x=0.55, y=0.0, z=0.93, q_x=0.707, q_y=0.0, q_z=0.707, q_w=0.0):
        self.x = x
        self.y = y
        self.z = z
        self.q = Quartets(q_x, q_y, q_z, q_w)

    def __str__(self):
        return '({} {} {}) - quartets: ({} {} {} {})'.format(self.x, self.y,
                                                             self.z, self.q.x,
                                                             self.q.y, self.q.z,
                                                             self.q.w)

joint_names = ['joint_1', 'joint_2', 'joint_3',
               'joint_4', 'joint_5', 'joint_6']

speed = 0.5
time = 0.25

goal = Coordinates()


def move_to(pub, positions, velocities, times):
    jt = JointTrajectory()
    jt.joint_names = joint_names
    jt.header.stamp = rospy.Time.now()

    for (position, velocity, time) in zip(positions, velocities, times):
        jtp = JointTrajectoryPoint()
        jtp.positions = position
        jtp.velocities = velocity
        jtp.time_from_start = rospy.Duration(time)
        jt.points.append(jtp)

    pub.publish(jt)
    rospy.loginfo("%s: starting %.2f sec traj", "self.controller_name",
                  times[-1])

def move_to_point(pub, joint_positions, speed, time):
    jt = JointTrajectory()
    jt.joint_names = joint_names
    jt.header.stamp = rospy.Time.now()

    jtp = JointTrajectoryPoint()
    jtp.positions = joint_positions
    jtp.velocities = [speed] * 6
    jtp.time_from_start = rospy.Duration(time)
    jt.points.append(jtp)

    pub.publish(jt)
    rospy.loginfo("%s: starting %.2f sec traj", "self.controller_name", time)


def parse_position_resp(pos_resp):
    if pos_resp.error_code.val == MoveItErrorCodes.SUCCESS:
        print('OK')
        return pos_resp.solution.joint_state.position
    elif pos_resp.error_code.val == MoveItErrorCodes.NO_IK_SOLUTION:
        print('No inverse kinematis solution')
    else:
        print('IK Error: {}'.format(pos_resp.error_code.val))


def solve_ik(goal):
    rospy.wait_for_service('compute_ik')
    try:
        print("try to solve ik...")
        request = GetPositionIKRequest()
        request.ik_request.group_name = "manipulator"
        request.ik_request.ik_link_name = "tool0"
        request.ik_request.attempts = 20
        request.ik_request.pose_stamped.header.frame_id = "/base_link"
        request.ik_request.pose_stamped.pose.position.x = goal.x
        request.ik_request.pose_stamped.pose.position.y = goal.y
        request.ik_request.pose_stamped.pose.position.z = goal.z
        request.ik_request.pose_stamped.pose.orientation.x = goal.q.x
        request.ik_request.pose_stamped.pose.orientation.y = goal.q.y
        request.ik_request.pose_stamped.pose.orientation.z = goal.q.z
        request.ik_request.pose_stamped.pose.orientation.w = goal.q.w
        ik = rospy.ServiceProxy('compute_ik', GetPositionIK)
        resp = ik(request)
        return parse_position_resp(resp)

    except rospy.ServiceException as e:
        print('Service call failed - {}'.format(e))


def main():
    rospy.init_node('tester', anonymous=True)
    rospy.sleep(0.5)

    sim_pub = rospy.Publisher('/arm_controller/command', JointTrajectory,
                          queue_size=10)

    fanuc_client = SimpleActionClient('move_group', MoveGroupAction)
    fanuc_client.wait_for_server()

    mg_action = MoveGroupAction()
    builder = MoveItGoalBuilder()
    builder.fixed_frame = 'base_link'
    builder.gripper_frame = 'tool0'
    builder.group_name = 'manipulator'

    c = ''
    while c != chr(27):
        print(rospy.wait_for_message('/joint_states', JointState))
        c = raw_input('input\n')
        if c == 'd':
            goal.x += 0.01
        elif c == 'a':
            goal.x -= 0.01
        elif c == 'w':
            goal.y += 0.01
        elif c == 's':
            goal.y -= 0.01
        elif c == 'e':
            goal.z += 0.01
        elif c == 'q':
            goal.z -= 0.01
        elif c == 'D':
            goal.q.x += 0.01
        elif c == 'A':
            goal.q.x -= 0.01
        elif c == 'W':
            goal.q.y += 0.01
        elif c == 'S':
            goal.q.y -= 0.01
        elif c == 'E':
            goal.q.z += 0.01
        elif c == 'Q':
            goal.q.z -= 0.01
        elif c == 'C':
            goal.q.w += 0.01
        elif c == 'Z':
            goal.q.w -= 0.01

        print(goal)

        position = solve_ik(goal)
        if position != None:
            builder.set_joint_goal(joint_names, position)
            builder.allowed_planning_time = time
            builder.plan_only = False
            mg_action.action_goal = builder.build()
            fanuc_client.send_goal(mg_action.action_goal)
            fanuc_client.wait_for_result()

            move_to_point(sim_pub, position, speed, time)

if __name__ == "__main__":
    main()