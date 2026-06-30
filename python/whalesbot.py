#coding=GB2312
#pro

'''
/*********************************************************/
/*                 声音ID 定义  # Sound_ID enum          */
/*********************************************************/
'''

sound_hi        = 1    #你好
sound_welcome   = 2    #欢迎
sound_thanks    = 3    #谢谢
sound_concerned = 4    #请多关照
sound_bye       = 5    #再见

sound_duck      = 6    #鸭
sound_bird      = 7    #鸟
sound_horse     = 8    #马-奔跑
sound_sheep     = 9    #羊咩
sound_cat       = 10   #猫
sound_dog       = 11   #狗
sound_cattle    = 12   #牛
sound_dinosaur  = 13   #恐龙
sound_cock      = 14   #公鸡

sound_airplane  = 15   #飞机
sound_helicopter = 16  #直升机
sound_horn      = 17   #汽车喇叭
sound_automobile = 18  #汽车发动
sound_cannon    = 19   #开炮
sound_tank      = 20   #坦克
sound_brake     = 21   #刹车

sound_heartbeat = 22   #心跳
sound_laugh     = 23   #大笑
sound_wow       = 24   #哇呜
sound_whistling = 25   #口哨

sound_piano_do  = 26   #钢琴
sound_piano_re  = 27   #钢琴
sound_piano_mi  = 28   #钢琴
sound_piano_fa  = 29   #钢琴
sound_piano_so  = 30   #钢琴
sound_piano_la  = 31   #钢琴
sound_piano_si  = 32   #钢琴
sound_piano_DO  = 33   #钢琴

sound_press_key = 46   #按键音

sound_hi_en 		= 54    #你好
sound_welcome_en	= 55    #欢迎
sound_concerned_en	= 56    #请多关照
sound_thanks_en		= 57    #谢谢
sound_bye_en		= 58    #再见


'''
/*********************************************************/
/*                 LED 符号ID 定义 LED_Symbol_ID         */
/*********************************************************/
'''

LED_symbol_question_mark    = 1		# ?
LED_symbol_exclamation      = 2 	# !
LED_symbol_dollar           = 3		#$
LED_symbol_RMB              = 4		#￥
LED_symbol_equal            = 5		#=
LED_symbol_plus             = 6 	#+
LED_symbol_minus            = 7 	#-
LED_symbol_multiplied       = 8 	#X
LED_symbol_divided          = 9 	#÷
LED_symbol_0 = 10	#0
LED_symbol_1 = 11	#1
LED_symbol_2 = 12	#2
LED_symbol_3 = 13	#3
LED_symbol_4 = 14	#4
LED_symbol_5 = 15	#5
LED_symbol_6 = 16	#6
LED_symbol_7 = 17	#7
LED_symbol_8 = 18	#8
LED_symbol_9 = 19	#9
LED_symbol_A = 20	#A
LED_symbol_B = 21	#B
LED_symbol_C = 22	#C
LED_symbol_D = 23	#D
LED_symbol_E = 24	#E
LED_symbol_F = 25	#F
LED_symbol_G = 26	#G
LED_symbol_H = 27	#H
LED_symbol_I = 28	#I
LED_symbol_J = 29	#J
LED_symbol_K = 30	#K
LED_symbol_L = 31	#L
LED_symbol_M = 32	#M
LED_symbol_N = 33	#N
LED_symbol_O = 34	#O
LED_symbol_P = 35	#P
LED_symbol_Q = 36	#Q
LED_symbol_R = 37	#R
LED_symbol_S = 38	#S
LED_symbol_T = 39	#T
LED_symbol_U = 40	#U
LED_symbol_V = 41	#V
LED_symbol_W = 42	#W
LED_symbol_X = 43	#X
LED_symbol_Y = 44	#Y
LED_symbol_Z = 45	#Z
LED_symbol_big_heart    = 46	#大心
LED_symbol_little_heart = 47	#小心
LED_symbol_forward      = 48	#前进
LED_symbol_backward     = 49	#后退
LED_symbol_turnleft     = 50	#左转
LED_symbol_turnright    = 51	#右转
LED_symbol_GO           = 52	#GO
LED_symbol_stop         = 53	#stop

'''
/*********************************************************/
/*                 LED 表情ID 定义 LED_Emo_ID            */
/*********************************************************/
'''

LED_emoji_eye     	= 1		#大眼睛
LED_emoji_smile   	= 2		#微笑
LED_emoji_sad     	= 3		#悲伤
LED_emoji_naughty 	= 4		#调皮
LED_emoji_surprised 	= 5		#惊讶
LED_emoji_flare   	= 6		#发怒
LED_emoji_tears   	= 7		#流泪
LED_emoji_avarice 	= 8		#贪财
LED_emoji_beckoning 	= 9		#心动
LED_emoji_anger   	= 10	#愤怒
LED_emoji_dizzy   	= 11	#晕
LED_emoji_grim    	= 12	#冷酷

'''
/*********************************************************/
/*                 电机ID 定义 Motor_ID                  */
/*********************************************************/
'''
MotorAll = 0
A = 1
B = 2
C = 3
D = 4
E = 5
F = 6

'''
/*********************************************************/
/*       路口巡线路口类型定义 Intersection_Type          */
/*********************************************************/
'''

intersection_left   = 0 	#左侧
intersection_T      = 1 	#T字/十字路口
intersection_right  = 2  	#右侧

'''
/*********************************************************/
/*                 巡线转弯-方向类型定义 Turn_Type       */
/*********************************************************/
'''

turn_left   = 0 	#左侧
turn_center = 1 	#中间
turn_right  = 2 	#右侧

'''
/*********************************************************/
/*                 图像识别-图像ID定义  AI_Image_ID      */
/*********************************************************/
'''

AI_images_0 	= 32		#0
AI_images_1 	= 16		#1
AI_images_2 	= 28		#2
AI_images_3 	= 26		#3
AI_images_4 	= 9		#4
AI_images_5		= 8		#5
AI_images_6 	= 24		#6
AI_images_7 	= 23		#7
AI_images_8 	= 7		#8
AI_images_9 	= 15	#9

AI_images_up        = 30	#上
AI_images_down      = 5	#下
AI_image_turn_left  = 12	#左转
AI_image_turn_right = 22	#右转
AI_image_turn_around_left   = 29	#左掉头
AI_image_turn_around_right = 31		#右掉头

AI_images_peach     = 18	#桃子
AI_images_pear      = 19	#梨
AI_images_cherry    = 2		#樱桃
AI_images_apple     = 0		#苹果
AI_images_banana    = 1		#香蕉

AI_images_mouse     = 14	#老鼠
AI_images_cattle    = 17	#牛
AI_images_tiger     = 27	#老虎
AI_images_rabbit    = 21	#兔子
AI_images_dragon    = 6		#龙
AI_images_snake     = 25	#蛇
AI_images_horse     = 11	#马
AI_images_goat      = 10	#山羊
AI_images_monkey    = 13	#猴子
AI_images_chicken   = 3		#鸡
AI_images_dog       = 4		#狗
AI_images_pig       = 20	#猪


'''
/*********************************************************/
/*                 图像识别-图像ID定义  AI_Voices_ID     */
/*********************************************************/
'''

AI_voices_stop      = 9		#停止
AI_voices_advance   = 1		#前进
AI_voices_turnright = 4		#右转
AI_voices_backward  = 2		#后退
AI_voices_startup   = 8		#启动
AI_voices_singsong  = 5		#唱首歌
AI_voices_turnleft  = 3		#左转
AI_voices_start     = 7		#开始
AI_voice_lightoff   = 12	#请关灯
AI_voice_lighton    = 11	#请开灯
AI_voices_dance     = 6		#跳支舞
AI_voice_turnaround  = 1	#转圈

'''
/*********************************************************/
/*    巡线 启动电机-传感器 比较运算符定义  Compare_Opt   */
/*********************************************************/
'''

compare_less_than       = 1
compare_greater_than    = 2
compare_equal       	= 3
compare_not_equal   	= 4

'''
/*********************************************************/
/*                        开关状态   Switch_State        */
/*********************************************************/
'''

switch_off = 0
switch_on  = 1

'''
/*********************************************************/
/*                        线型   Line_Type               */
/*********************************************************/
'''

black_line 	= 1 #黑线
white_line  = 2 #白线

'''
/*********************************************************/
/*                        移动方向                       */
/*********************************************************/
'''

move_forward 	= 1
move_backward  	= 2
move_turnleft  	= 3
move_turnright  = 4


'''
/*********************************************************/
/*                        舵机ID定义                      */
/*********************************************************/
'''
S1 	= 1
S2  = 2
S3  = 3
S4  = 4
S5  = 5
S6  = 6
S7  = 7
S8  = 8
S9  = 9
S10  = 10
S11  = 11
S12  = 12
S13  = 13
S14  = 14
S15  = 15
S16  = 16
S17  = 17
S18  = 18

'''
/*********************************************************/
/*                        端口ID定义                     */
/*********************************************************/
'''
P1 	= 1
P2  = 2
P3  = 3
P4  = 4
P5  = 5
P6  = 6
P7  = 7
P8  = 8
P9  = 9
P10  = 10
P11  = 11
P12  = 12

'''
/*********************************************************/
/*                        按键ID定义                     */
/*********************************************************/
'''
key_enter  	= 1
key_left  	= 2
key_right  	= 3
key_up  	= 2
key_down  	= 3


'''
/*********************************************************/
/*                        颜色ID定义                     */
/*********************************************************/
'''
color_white  	= 1	#白
color_yellow  	= 2	#黄
color_purple  	= 3	#紫
color_cyan  	= 4	#青
color_red	  	= 5	#红
color_green  	= 6	#绿
color_blue  	= 7	#蓝
color_black  	= 8	#黑

'''
/*********************************************************/
/*                        电机转动方向                    */
/*********************************************************/
'''
Motor_CW = 1
Motor_CCW = 2

'''
/*********************************************************/
/*                        音符ID                         */
/*********************************************************/
'''
C5 = 1
D5 = 2
E5 = 3
F5 = 4
G5 = 5
A5 = 6
B5 = 7
C6 = 8

'''
/*********************************************************/
/*                        ID                             */
/*********************************************************/
'''
omni_turnleft = 1
omni_turnright = 2


#电机设置
def set_motor(motor_id, speed):
	"""
	return:void
	args:int,int
	"""
	pass
#设置双电机时间
def set_dual_motor_time(motor1_id, motor1_speed, motor2_id, motor2_speed, time):
	"""
	return:void
	args:int,int,int,int,float
	"""
	pass
#设置单电机时间
def set_motor_time(motor_id, motor_speed, time):
	"""
	return:void
	args:int,int,float
	"""
	pass
#设置双电机编码器
def set_dual_motor_angle(motor1_id, motor1_speed, motor2_id, motor2_speed, angle):
	"""
	return:void
	args:int,int,int,int,int
	"""
	pass
#设置电机角度闭环
def set_motor_angle(motor_id, motor_speed, angle):
	"""
	return:void
	args:int,int,int
	"""
	pass
#反转电机
def reverse_motor(motor_id):
	"""
	return:void
	args:int
	"""
	pass
#设置电机方向
def set_motor_direction(motorId, speed, direction):
	"""
	return:void
	args:int,int,int
	"""
	pass
#设置电机圈数
def set_motor_cycles(motorId, speed, cycles):
	"""
	return:void
	args:int,int,int
	"""
	pass
#设置两个电机
def set_double_motor(motor1_Id, motor1_speed, motor2_Id, motor2_speed):
	"""
	return:void
	args:int,int,int,int
	"""
	pass
#设置两个电机时间
def set_double_motor_time(motor1_Id, motor1_speed, motor2_Id, motor2_speed, secs):
	"""
	return:void
	args:int,int,int,int,float
	"""
	pass
#关闭电机
def off_motor(motor_id):
	"""
	return:void
	args:int
	"""
	pass
	
#移动
def move(move_type, speed):
	"""
	return:void
	args:int,int
	"""
	pass
#移动时间
def move_time(move_type, speed, time):
	"""
	return:void
	args:int,int,float
	"""
	pass
#移动圈数
def move_cycles(move_type, speed, cycles):
	"""
	return:void
	args:int,int,int
	"""
	pass
#移动双圈数
def move_double_cycles(cycles1, cycles2, speed):
	"""
	return:void
	args:int,int,int
	"""
	pass
#停止移动
def stop_move():
	"""
	return:void
	"""
	pass
#声音
def play_sound(sound_id):
	"""
	return:void
	args:int
	"""
	pass
#指示灯
def set_light( port_id, state):
	"""
	return:void
	args:int,int
	"""
	pass
#电磁铁
def set_magnet( port_id, state):
	"""
	return:void
	args:int,int
	"""
	pass
#LED 表情
def display_emotion(left_port_id, right_port_id, emotiom_id):
	"""
	return:void
	args:int,int,int
	"""
	pass
#关闭表情
def off_emotion(left_port_id, right_port_id):
	"""
	return:void
	args:int,int
	"""
	pass
#LED符号
def display_symbol(port_id, symbol_id):
	"""
	return:void
	args:int,int
	"""
	pass
#LED自定义
def display_custom(port_id, led_maritx):
	"""
	return:void
	args:int,int
	"""
	pass
#关闭LED
def off_LED(port_id):
	"""
	return:void
	args:int
	"""
	pass
#读数
def read_number(number):
	"""
	return:void
	args:int
	"""
	pass
#显示
def show(line, string):	
	"""
	return:void
	args:int,string
	"""
	pass
#设置舵机角度模式
def set_servo_angle(servo_id, speed, angle):
	"""
	return:void
	args:int,int,int
	"""
	pass
#设置舵机旋转模式
def set_servo_rotation(servo_id, speed):
	"""
	return:void
	args:int,int
	"""
	pass
#读取舵机ID
def Servo_IDscan():
	"""
	return:int
	"""
	pass
#设置舵机角度模式 m2
def set_servo_angle_m2(servo_id, speed, angle):
	"""
	return:void
	args:int,int,int
	"""
	pass
#设置舵机旋转模式 m2
def set_servo_rotation_m2(servo_id, speed):
	"""
	return:void
	args:int,int
	"""
	pass

#播放动作页
def play_page(page):
	"""
	return:void
	args:int
	"""
	pass
#等待动作结束
def quit_page():
	"""
	return:void
	"""
	pass

#停止动作页
def stop_page(page):
	"""
	return:void
	"""
	pass

#设置音符
def buzzer_note(pitch, duration):
	"""
	return:void
	args:int,int
	"""
	pass

#数码管
def display_digital_tube(port_id, value):
	"""
	return:void
	args:int,int
	"""
	pass
#数码管比分显示
def display_digital_tube_score(port_id, score1, score2):
	"""
	return:void
	args:int,int,int
	"""
	pass
#关闭数码管
def off_digital_tube(port_id):
	"""
	return:void
	args:int
	"""
	pass
#数码管 module 2
def display_digital_tube_m2(port_id, value):
	"""
	return:void
	args:int,int
	"""
	pass

#清空数码管 module 2
def clear_digital_tube_m2(port_id):
	"""
	return:void
	args:int
	"""
	pass

#屏幕 数码管 module 2
def display_screen(value):
	"""
	return:void
	args:int
	"""
	pass

#清空 屏幕 数码管 module 2
def clear_screen():
	"""
	return:void
	"""
	pass
#彩色LED
def set_RGB(port_id, colorR, colorG, colorB):
	"""
	return:void
	args:int,int,int,int
	"""
	pass
#彩色LED
def set_RGB_color(port_id, color_id):
	"""
	return:void
	args:int,int
	"""
	pass
#关闭彩色LED
def off_RGB_color(port_id):
	"""
	return:void
	args:int
	"""
	pass

#显示文本
def display_text(str):
	"""
	return:void
	args:string
	"""
	pass
#显示文本
def display_line(line, string):	
	"""
	return:void
	args:int,string
	"""
	pass
#录音
def recorder(port_id):
	"""
	return:void
	args:int
	"""
	pass
#播放录音
def play_record():
	"""
	return:void
	"""
	pass

#集成灰度
def get_integrated_grayscale(port_id, channel_id):
	"""
	return:int
	args:int,int
	"""
	pass
#集成灰度 检测到 (黑线，白线)
def integrated_grayscale_detected(port_id, channel_id, line_type):
	"""
	return:int
	args:int,int,int
	"""
	pass

#红外测距
def get_infrared_distance(port_id):
	"""
	return:int
	args:int
	"""
	pass
#红外检测到障碍物
def obstacle_infrared_detected(port_id):
	"""
	return:int
	args:int
	"""
	pass
#触碰开关
def touch_switch_pressed(port_id):
	"""
	return:int
	args:int
	"""
	pass
#环境光
def get_ambient_light(port_id):
	"""
	return:int
	args:int
	"""
	pass
#单灰度
def get_single_grayscale(port_id):
	"""
	return:int
	args:int
	"""
	pass
#单灰度 检测到 (黑线，白线)
def single_grayscale_detected(port_id, line_type):
	"""
	return:int
	args:int,int
	"""
	pass
#温度传感器
def get_temperature(port_id):
	"""
	return:int
	args:int
	"""
	pass
#湿度传感器
def get_humidity(port_id):
	"""
	return:int
	args:int
	"""
	pass
#火焰传感器
def get_flame(port_id):
	"""
	return:int
	args:int
	"""
	pass
#磁敏传感器
def magnetic_detected(port_id):
	"""
	return:int
	args:int
	"""
	pass
#超声传感器
def get_ultrasonic_distance(port_id):
	"""
	return:int
	args:int
	"""
	pass
#定时器
def timer():
	"""
	return:float
	"""
	pass
#时钟复位
def reset_timer():
	"""
	return:void
	"""
	pass
#
def get_sound_volume(port_id):
	"""
	return:int
	args:int
	"""
	pass
#

#按键
def button_pressed(key_id):
	"""
	return:int
	args:int
	"""
	pass

#遥控器
def get_bt_remote_control(button_id):
	"""
	return:int
	args:int
	"""
	pass

#电机编码器
def motor_encoder(servo_id):
	"""
	return:int
	args:int
	"""
	pass

#重置电机编码器
def reset_motor_encoder(servo_id):
	"""
	return:void
	args:int
	"""
	pass

#触碰传感器事件
def touch_event(port_id):
	"""
	return:int
	args:int
	"""
	pass

#修改舵机Id
def servo_id_change(oldId, newId):
	"""
	return:void
	args:int,int
	"""
	pass

#获取颜色传感器值
def color_value(port_id):
	"""
	return:int
	args:int
	"""
	pass

#检测颜色传感器是否识别到 颜色 color_id
def color_detected(port_id, color_id):
	"""
	return:int
	args:int,int
	"""
	pass

#手势识别
def get_gesture(port_id):
	"""
	return:int
	args:int
	"""
	pass

#激光测距
def get_tof(port_id):
	"""
	return:int
	args:int
	"""
	pass

#气压传感器
def get_pressure(port_id, type):
	"""
	return:int
	args:int,int
	"""
	pass

#磁敏传感器
def magnetic_encoder(port_id, channel):
	"""
	return:int
	args:int,int
	"""
	pass

'''
/*********************************************************/
/*                   数学                                 */
/*********************************************************/
'''
def random_number(min, max):
	"""
	return:int
	args:int,int
	"""
	pass
#余数
def math_modulus(a, b):
	"""
	return:float
	args:int,int
	"""
	pass

def math_round(a, b):
	"""
	return:int
	args:float
	"""
	pass

def math_abs(n):
	"""
	return:float
	args:float
	"""
	pass

def math_floor(n):
	"""
	return:float
	args:float
	"""
	pass

def math_ceiling(n):
	"""
	return:float
	args:float
	"""
	pass

def math_sqrt(n):
	"""
	return:float
	args:float
	"""
	pass

def math_sin(n):
	"""
	return:float
	args:float
	"""
	pass

def math_cos(n):
	"""
	return:float
	args:float
	"""
	pass

def math_tan(n):
	"""
	return:float
	args:float
	"""
	pass

def math_asin(n):
	"""
	return:float
	args:float
	"""
	pass

def math_acos(n):
	"""
	return:float
	args:float
	"""
	pass

def math_atan(n):
	"""
	return:float
	args:float
	"""
	pass

def math_ln(n):
	"""
	return:float
	args:float
	"""
	pass

def math_log(n):
	"""
	return:float
	args:float
	"""
	pass

def math_exp(n):
	"""
	return:float
	args:float
	"""
	pass

def math_pow10(n):
	"""
	return:float
	args:float
	"""
	pass

#m0
def beep_play(type, id):
	"""
	return:void
	args:int,int
	"""
	pass

def beep_tone(time, id):
	"""
	return:void
	args:int,int
	"""
	pass

'''
/*********************************************************/
/*                   高级                                 */
/*********************************************************/
'''
#数字输入
def get_digital_input(port_id):
	"""
	return:int
	args:int
	"""
	pass

#数字输出
def set_digital_output(port_id, state):
	"""
	return:void
	args:int,int
	"""
	pass
#模拟输入
def get_analog_input(port_id):
	"""
	return:int
	args:int
	"""
	pass
#读 EEPROM
def read_EEPROM(address):
	"""
	return:int
	args:int
	"""
	pass
#写 EEPROM
def write_EEPROM(address, value):
	"""
	return:void
	args:int,int
	"""
	pass
#图像识别
def get_AI_image(port_id):
	"""
	return:int
	args:int
	"""
	pass
#语音识别
def get_AI_voice():
	"""
	return:int
	"""
	pass

#AI巡线初始化
def Init_lane(port, mode, threshold, lan_width, baseline):
	"""
	return:void
	args:int,int,int,int,int
	"""
	pass

#AI巡路速度
def patr_XX(speed):
	"""
	return:void
	args:int
	"""
	pass

#AI巡路计时
def patr_time1(speed, time):
	"""
	return:void
	args:int,float
	"""
	pass

#AI巡路到路口
def patr_road1(crossroad_id, speed, time):
	"""
	return:void
	args:int,int,float
	"""
	pass

#AI巡路转弯
def patr_turn1(offset, left_speed, right_speed):
	"""
	return:void
	args:int,int,int
	"""
	pass

#AI巡线速度
def patr_XL(speed):
	"""
	return:void
	args:int
	"""
	pass
#AI巡线计时
def patr_time2(speed, time):
	"""
	return:void
	args:int,float
	"""
	pass

#AI巡线到路口
def patr_road2(crossroad_id, speed, time):
	"""
	return:void
	args:int,int,float
	"""
	pass

#AI巡线转弯
def patr_turn2(offset, left_speed, right_speed):
	"""
	return:void
	args:int,int,int
	"""
	pass

#AI视觉识别
def AI_read_value(port_id, mode):
	"""
	return:void
	args:int,int
	"""
	pass

#AI视觉灯光
def AI_set(port_id, reg_addr, data):
	"""
	return:void
	args:int,int,int
	"""
	pass

#巡线初始化 集成灰度
def patrol_integrated_initialization(left_motor_id, left_motor_speed, right_motor_id, right_motor_speed):
	"""
	return:void
	args:int,int,int,int
	"""
	pass
#巡线初始化 集成灰度
def patrol_integrated_init_m6(left_motor_speed, right_motor_speed, line_gray, bg_gray):
	"""
	return:void
	args:int,int,int,int
	"""
	pass
#巡线初始化 单灰度
def patrol_single_initialization(left_motor_id, left_motor_speed, right_motor_id, right_motor_speed, p1, p2, p3, p4, p5):
	"""
	return:void
	args:int,int,int,int,int,int,int,int,int
	"""
	pass
#
def patrol_init_mecanum_wheel_integrated(LB_speed, RB_speed, LF_speed, RF_speed):
	"""
	return:void
	args:int,int,int,int
	"""
	pass
#
def patrol_init_mecanum_wheel_single(LB_speed, RB_speed, LF_speed, RF_speed, p1, p2, p3, p4, p5):
	"""
	return:void
	args:int,int,int,int,int,int,int,int,int
	"""
	pass
# m6
def patr_Mecanum_wheel_init(LB_speed, RB_speed, LF_speed, RF_speed, line_gray, bg_gray):
	"""
	return:void
	args:int,int,int,int,int,int
	"""
	pass
#
def patrol_ambient_detection():
	"""
	return:void
	"""
	pass
#巡线 走线
def Zx(speed, value):
	"""
	return:void
	args:int,int
	"""
	pass
#巡线 巡线速度
def patrol_speed(speed):
	"""
	return:void
	args:int
	"""
	pass
#巡线 路口巡线
def patrol_road(type ,speed, time):
	"""
	return:void
	args:int,int,int
	"""
	pass
#巡线 按时巡线
def patrol_time(speed, time):
	"""
	return:void
	args:int,int
	"""
	pass
#巡线 巡线转弯
def patrol_turn(turn_type, left_speed, right_speed):
	"""
	return:void
	args:int,int,int
	"""
	pass
#巡线 启动电机-时间
def start_motor_time(left_speed, right_speed, time):
	"""
	return:void
	args:int,int,int
	"""
	pass
#巡线 启动电机-角度
def start_motor_angle(left_speed, right_speed, angle):
	"""
	return:void
	args:int,int,int
	"""
	pass
#巡线 启动电机-传感器
def start_motor_sensor(left_speed, right_speed, sensor_port_id, compare_opt, compare_value):
	"""
	return:void
	args:int,int,int,int,int
	"""
	pass
#巡线 启动电机-传感器
def motor_sensor(left_speed, right_speed, sensor_port_id, compare_opt, compare_value):
	"""
	return:void
	args:int,int,int,int,int
	"""
	pass
#巡线 启动按钮
def patrol_button():
	"""
	return:void
	"""
	pass
def Printf(chStr):
	"""
	return:void
	args:int
	"""
	pass
def setDO(Channel, State):
	"""
	return:void
	args:int,int
	"""
	pass
def music(idx):
	"""
	return:void
	args:int
	"""
	pass
def set_servo(id , iSpeed, iPos):
	"""
	return:void
	args:int,int,int
	"""
	pass
def  JY_AI( Channel):
	"""
	return:int
	args:int
	"""
	pass
def  switch_state(nChannel):
	"""
	return:int
	args:int
	"""
	pass
def  button_state(nKeyIndex):
	"""
	return:int
	args:int
	"""
	pass
def seconds():
	"""
	return:float
	"""
	pass
def reset_time():
	"""
	return:void
	"""
	pass
def wait(sec):
	"""
	return:void
	args:int
	"""
	pass
def  rand(nMinLimit, nMaxLimit):
	"""
	return:int
	args:int,int
	"""
	pass
def  eeprom_read(hwAddress, hwLength, pchByte):
	"""
	return:int
	args:int,int,int
	"""
	pass
def  eeprom_write(hwAddress, hwLength, pchByte):
	"""
	return:void
	args:int,int,int
	"""
	pass
def patr_init(ch1, ch2):
	"""
	return:void
	args:int,int
	"""
	pass
def patr_environmental_acquiment():
	"""
	return:void
	"""
	pass
def patr_road(para1, para2, para3):
	"""
	return:void
	args:int,int,int
	"""
	pass
def patr_time(para1, para2):
	"""
	return:void
	args:int,int
	"""
	pass
def patr_turn(para1, para2, para3):
	"""
	return:void
	args:int,int,int
	"""
	pass
def patr_motor():
	"""
	return:void
	"""
	pass
def patr_button():
	"""
	return:void
	"""
	pass
#启动电机时间
def motor_time(Lspeed, Rspeed, time):
	"""
	return:void
	args:int,int,float
	"""
	pass

#std
def PlaySensorNum(num):
	"""
	return:void
	args:int
	"""
	pass


#MakeU b1

def move_b1(move_type, speed):
	"""
	return:void
	args:int,int
	"""
	pass
    
def move_time_b1(move_type, speed, time):
	"""
	return:void
	args:int,int,float
	"""
	pass
    
def move_angle_b1(move_type, speed, angle):
	"""
	return:void
	args:int,int,int
	"""
	pass
    
def move_stop_b1():
	"""
	return:void
	"""
	pass
def set_motor_b1(motor_id, speed):
	"""
	return:void
    args:int,int
	"""
	pass
def set_dual_motor_b1(speed_A, speed_B):
	"""
	return:void
    args:int,int
	"""
	pass
def off_motor_b1(motor_id):
	"""
	return:void
    args:int
	"""
	pass
def set_external_motor_b1(speed):
	"""
	return:void
    args:int
	"""
	pass
def off_external_motor_b1():
	"""
	return:void
	"""
	pass
    
def set_control_light_b1(color):
	"""
	return:void
    args:int
	"""
	pass
def play_sound_b1(sound_Id):
	"""
	return:void
    args:int
	"""
	pass
def set_ultrasonic_light_b1(switch):
	"""
	return:void
    args:int
	"""
	pass
def get_ultrasonic_distance_b1():
	"""
	return:int
	"""
	pass
def obstacle_ultrasonic_detected_b1():
	"""
	return:int
	"""
	pass
#超声检测到障碍物
def obstacle_ultrasonic_detected(port):
	"""
	return:int
	args:int
	"""
	pass
def patrol_road_b1(type, speed, time):
	"""
	return:void
    args:int,int,float
	"""
	pass
def patrol_time_b1(speed, time):
	"""
	return:void
    args:int,float
	"""
	pass
def patrol_turn_b1(type, speed_A, speed_B):
	"""
	return:void
    args:int,int,int
	"""
	pass
def patrol_move_time_b1(speed_A, speed_B, time):
	"""
	return:void
    args:int,int,float
	"""
	pass
def patrol_move_angle_b1(speed_A, speed_B, angle):
	"""
	return:void
    args:int,int,int
	"""
	pass
def patrol_stop_b1():
	"""
	return:void
	"""
	pass

# m6
def set_encoder_motor(Id, port, power):
	"""
	return:void
    args:int,int,int
	"""
	pass
def set_dc_motor(Id, port, power):
	"""
	return:void
    args:int,int,int
	"""
	pass
def set_smart_servo_angle(Id, power, angle):
	"""
	return:void
    args:int,int,int
	"""
	pass
def set_smart_servo(Id, power):
	"""
	return:void
    args:int,int
	"""
	pass
def set_smart_servo_id(Id, newId):
	"""
	return:void
    args:int,int
	"""
	pass
#def set_servo(Id, power, angle):
#	"""
#	return:void
#    args:int,int,int
#	"""
#	pass
def set_servo_fast(Id, power):
	"""
	return:void
    args:int,int
	"""
	pass
def set_electromagnet(port, status):
	"""
	return:void
    args:int,int
	"""
	pass

#def set_digital_output(port, value):
#	"""
#	return:void
#    args:int,int
#	"""
#	pass

def robotic_arm_init(offset1, offset2, offset3):
	"""
	return:void
    args:int,int,int
	"""
	pass

def robotic_arm_set_pos(x, y, z, speed):
	"""
	return:void
    args:float,float,float,int
	"""
	pass

def robotic_arm_rotate_set_pos(rotate, y, z, speed):
	"""
	return:void
    args:int,float,float,int
	"""
	pass

def set_emotion(emotionId, LPort, RPort):
	"""
	return:void
    args:int,int,int
	"""
	pass
#def off_emotion(left_port_id, right_port_id):
#	"""
#	return:void
#	args:int,int
#	"""
#	pass

def set_symbol(emotionId, port):
	"""
	return:void
    args:int,int
	"""
	pass
def set_symbol_cust(d1, d2, d3, d4, d5, d6, d7, d8, port):
	"""
	return:void
    args:int,int,int,int,int,int,int,int,int
	"""
	pass
def off_led_matrix(port):
	"""
	return:void
    args:int
	"""
	pass
def set_digital_tube(port, value):
	"""
	return:void
    args:int,int
	"""
	pass
def clear_digital_tube(port):
	"""
	return:void
    args:int
	"""
	pass
def set_led_light_rgb(port, r, g, b):
	"""
	return:void
    args:int,int,int,int
	"""
	pass
def set_led_light_color(port, color):
	"""
	return:void
    args:int,int
	"""
	pass
def off_led_light(port):
	"""
	return:void
    args:int
	"""
	pass
def set_rgb_led_module(port, id, r, g, b):
	"""
	return:void
    args:int,int,int,int,int
	"""
	pass
def set_rgb_led_strip(port, id, r, g, b):
	"""
	return:void
    args:int,int,int,int,int
	"""
	pass
#def beep_play(port, duration):
#	"""
#	return:void
#    args:int,int
#	"""
#	pass
def gray_detected_line(port, line_type):
	"""
	return:int
    args:int,int
	"""
	pass
def gray_value(port):
	"""
	return:int
    args:int
	"""
	pass
def integrated_gray_value(port):
	"""
	return:int
    args:int
	"""
	pass
def flame_value(port):
	"""
	return:int
    args:int
	"""
	pass
def temperature_value(port):
	"""
	return:int
    args:int
	"""
	pass
def humidity_value(port):
	"""
	return:int
    args:int
	"""
	pass
def volume_value(port):
	"""
	return:int
    args:int
	"""
	pass
def ambient_light_value(port):
	"""
	return:int
    args:int
	"""
	pass
def ultrasonic_detection_distance(port):
	"""
	return:int
    args:int
	"""
	pass
def gas_pressure(port):
	"""
	return:int
    args:int
	"""
	pass
def infrared_value(port):
	"""
	return:int
    args:int
	"""
	pass
def infrared_receiver(port):
	"""
	return:int
    args:int
	"""
	pass
def human_infrared_value(port):
	"""
	return:int
    args:int
	"""
	pass
def potentiometer(port):
	"""
	return:int
    args:int
	"""
	pass
def bluetooth_receiver():
	"""
	return:int
	"""
	pass
def bluetooth_stick(key):
	"""
	return:int
    args:int
	"""
	pass
def jointed_arm(port, axis):
	"""
	return:int
    args:int,int
	"""
	pass
def touch_button(port):
	"""
	return:int
    args:int
	"""
	pass
def key_button(port, key):
	"""
	return:int
    args:int,int
	"""
	pass
def gyroscope(port, axis):
	"""
	return:int
    args:int,int
	"""
	pass
def limit_switch(port):
	"""
	return:int
    args:int
	"""
	pass
def water_temperature(port):
	"""
	return:int
    args:int
	"""
	pass
def analog_input(port):
	"""
	return:int
    args:int
	"""
	pass
def time_value():
	"""
	return:int
	"""
	pass
def reset_time_value():
	"""
	return:void
	"""
	pass

#def color_value(port):
#	"""
#	return:int
#   args:int
#	"""
#	pass

#def color_detected(port, color):
#	"""
#	return:int
#   args:int,int
#	"""
#	pass

#def get_AI_image(port):
#	"""
#	return:int
#   args:int
#	"""
#	pass

def restore_torque():
	"""
	return:void
	"""
	pass

def mecanum_wheel_ctrl(power, angle):
	"""
	return:void
	args:int,int
	"""
	pass

def mecanum_wheel_turn(direction, power):
	"""
	return:void
	args:int,int
	"""
	pass

def LCD_ClearBuffer():
	"""
	return:void
	"""
	pass

def ClearLCD():
	"""
	return:void
	"""
	pass

def get_motion_file_running_state():
	"""
	return:int
	"""
	pass

def getAI(port):
	"""
	return:int
    args:int
	"""
	pass

#设置直流电机
def set_motor_open(port, speed):
	"""
	return:void
	args:int,int
	"""
	pass
