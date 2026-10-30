## Universal Robots

Run the following command to start the UR5e gazebo simulation, which has been installed automatically with OpenHRC:


The target robot type `UR_TYPE` needs to be chosen from `{ur3, ur5, ur10, ur3e, ur5e, ur7e, ur10e, ur12e, ur16e, ur8long, ur15, ur18, ur20, ur30}`.


```bash
ros2 launch ur_simulation_gz ur_sim_control.launch.py ur_type:={UR_TYPE} initial_joint_controller:=forward_velocity_controller launch_rviz:=false
```
Then use robot:=ur5 e.g.:

```bash
ros2 launch ohrc_teleoperation marker_teleoperation.launch.py robot:=ur5
```


## Franka Research 3 & Franka Emika (Panda)

Run the following command to start the Franka3 gazebo simulation, which has been installed automatically with OpenHRC if selected during setup:

```bash
ros2 launch ohrc_hw_config fr3_gazebo.launch.py
```

or

```bash
ros2 launch ohrc_hw_config panda_gazebo.launch.py
```

Then use robot:=fr3 or robot:=panda e.g.:

```bash
ros2 launch ohrc_teleoperation marker_teleoperation.launch.py robot:=fr3
```


## xARM

Run the following command to start the xArm gazebo simulation, which has been installed automatically with OpenHRC if selected during setup:

```bash
ros2 ros2 launch ohrc_hw_config bringup_xarm6_sim.launch.py
```

Then use robot:=fr3 e.g.:

```bash
ros2 launch ohrc_teleoperation marker_teleoperation.launch.py robot:=xarm6
```


## CRANE-X7

Run the following command to start the CRANE-X7 gazebo simulation, which has been installed automatically with OpenHRC if selected during setup:

```bash
ros2 launch ohrc_hw_config crane_x7_sim_control.launch.py
```

Then use robot:=crane_x7 e.g.:

```bash
ros2 launch ohrc_teleoperation marker_teleoperation.launch.py robot:=crane_x7
```


## myCobot 280 (M5)

Run the following command to start the myCobot 280 simulation, which has been installed automatically with OpenHRC if selected during setup:

```bash
ros2 launch ohrc_hw_config mycobot_sim_control.launch.py
```

Then use robot:=mycobot e.g.:

```bash
ros2 launch ohrc_teleoperation marker_teleoperation.launch.py robot:=mycobot
```
