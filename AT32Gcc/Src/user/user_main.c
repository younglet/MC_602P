#include "whalesbot.h"

/*
M1 ：左前轮，正转后退
M2 ：左后轮，正转后退
M3 ：右后轮，正转前进
M4 ：右前轮，正转前进
M5：转盘电机
M6：导轨电机，正转后撤

P1：导轨后磁敏
P2：导轨前磁敏
P3：转盘磁敏
*/

int Key=0;              //  普通按键
int L_FB=0;             // 左摇杆Y，前后值
int L_LR=0;             // 左摇杆X，左右值
int R_FB=0;             // 右摇杆Y，前后值
int R_LR=0;             // 右摇杆X，左右值

int Stop=10;            //摇杆复位值偏差

float fast=0.50;            //电机高速速度系数
float low=0.25;             //电机低速速度系数

int speed_futher_1=0;     //M1将要设置的目标速度
int speed_futher_2=0;     //M2将要设置的目标速度
int speed_futher_3=0;     //M3将要设置的目标速度
int speed_futher_4=0;     //M4将要设置的目标速度

int angle_YTFY=-90;          //云台俯仰舵机最低位置


void Move(int Speed_1,int Speed_2,int Speed_3,int Speed_4)      //麦克纳姆轮运动控制
{
    set_motor(M1,Speed_1);      //左前轮，正转后退
    set_motor(M2,Speed_2);      //左后轮，正转后退
    set_motor(M3, -Speed_3);      //右后轮，正转前进
    set_motor(M4, -Speed_4);      //右前轮，正转前进
}

void Remote_control()           //获取并处处理遥控器键值
{
    while((float)get_bt_remote_control(BTSTICK1)==0)        //左摇杆返回值如果为0，判断为遥控器未连接。
        {
            Move(0,0,0,0);
            beep_play(F_C5,0.1);
            wait(0.1);
        }
    Key=(float)get_bt_remote_control(BTKEY);                    //获取按键值
    L_FB=(float)get_bt_remote_control(BTSTICK1)-100;        //获取左摇杆前后值
    L_LR=(float)get_bt_remote_control(BTSTICK2)-100;        //获取左摇杆左右值
    R_FB=(float)get_bt_remote_control(BTSTICK3)-100;        //获取左摇杆前后值
    R_LR=(float)get_bt_remote_control(BTSTICK4)-100;        //获取左摇杆左右值
    if(math_abs(L_FB)<Stop) L_FB=0;
    if(math_abs(L_LR)<Stop) L_LR=0;
    if(math_abs(R_FB)<Stop) R_FB=0;
    if(math_abs(R_LR)<Stop) R_LR=0;
}


void user_main()
{
    float Power=0.3;    //电机规律系数
    int angle=0;           //云台俯仰舵机角度值
    angle=angle_YTFY;
    set_servo_angle(S1,40,angle);

    while(1)
    {
        Remote_control();
        
        speed_futher_1=(L_FB+L_LR)*Power;
        speed_futher_2=(L_FB-L_LR)*Power;
        speed_futher_3=(L_FB+L_LR)*Power;
        speed_futher_4=(L_FB-L_LR)*Power;
        Move(speed_futher_1,speed_futher_2,speed_futher_3,speed_futher_4); 
        
         if(R_FB<0) angle=angle+2;                //云台俯仰舵机抬头
            else if(R_FB>0) angle=angle-2;     //云台俯仰舵机低头
        if(angle<angle_YTFY) angle=angle_YTFY;                        //云台俯仰舵机角度控制
            else if(angle>(angle_YTFY+200)) angle=angle_YTFY+180;       //云台俯仰舵机角度控制
         set_servo_angle(S1,40,angle);                  //云台俯仰舵机运动
        
        
        switch(Key)
        {
            case 0: //没有按键被按下
            {
               
            }
                break;
            case 1: //左-上键，低速前进
                Move(100*low, 100*low, 100*low, 100*low);
                break;
            case 2: //左-左键，低速左平移
                Move(-100*low, 100*low, -100*low, 100*low);
                break;
            case 4: //左-下键，低速后退
                Move(-100*low, -100*low, -100*low, -100*low);
                break;
            case 8: //左-右键，低速右平移
                Move(100*low, -100*low, 100*low, -100*low);
                break;
            case 16: //右-上键，俯仰低头
                angle=angle-2;
                break;
            case 32: //右-右键，低速右转
                Move(100*low, 100*low, -100*low, -100*low);
                break;
            case 64: //右-下键，俯仰抬头
                angle=angle+2;
                break;
            case 128: //右-左键，低速左转
                Move(-100*low, -100*low, 100*low, 100*low);
                break;
            case 256: //PS2遥控器左1键、Pro控制器左中键
                Power=low;
                break;
            case 512: //PS2遥控器左2键、Pro控制器右中键
                Power=fast;
                break;
            case 1024: //Pro控制器3键，发射
                set_magnet(P6,switch_off);
                while(! touch_switch_pressed(P2))  set_motor(M6, -30);
                    set_motor(M6, 0);
                set_magnet(P6,switch_on); wait(0.5);
                while(! touch_switch_pressed(P1))  set_motor(M6, 30);
                    set_motor(M6, 0);
                
                set_motor(M5, 4);
                while(! touch_switch_pressed(P3)) {}
                while( touch_switch_pressed(P3)) {}
                    set_motor(M5, 0);
             
                break;
            case 2048: //Pro控制器4键，发射
                set_magnet(P6,switch_off);
                break;
            case 16384: //Pro控制器1键，后撤拉回
                set_magnet(P6,switch_on);
                while(! touch_switch_pressed(P1))  set_motor(M6, 30);
                    set_motor(M6, 0);
                break;
            case 32768: //Pro控制器2键，前进释放
                while(! touch_switch_pressed(P2))  set_motor(M6, -30);
                    set_motor(M6, 0);
                break;
        } 
        /*
        if((speed_now_1*speed_futher_1<0) || (speed_now_2*speed_futher_2<0) || (speed_now_3*speed_futher_3<0) || (speed_now_4*speed_futher_4<0))
        {
            Move(0,0,0,0);
            wait(0.2);
        }
        Move(speed_futher_1,speed_futher_2,speed_futher_3,speed_futher_4); 
        speed_now_1 = speed_futher_1;
        speed_now_2 = speed_futher_2;
        speed_now_3 = speed_futher_3;
        speed_now_4 = speed_futher_4;
        */
        show(3,"%d",Key);
    }
}
