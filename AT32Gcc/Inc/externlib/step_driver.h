#ifndef EXTERNLIB_STEPDRIVER_H_
#define EXTERNLIB_STEPDRIVER_H_
#ifdef EXTERNLIB_STEPDRIVER_H_


//对应3个步进电机
#define STP_MOT_CH1   1
#define STP_MOT_CH2   2
#define STP_MOT_CH3   3

//设置步进电机旋转，speed：-32000~32000，（根据不同步进电机，确定最大可设定速度）
void set_stepmotor(int ch,int speed);

//获取步进驱动器的步进计数
int get_stepmotor_distance(int ch);

//电机加减速平滑程度：acc: 0~32000（数值越大,加速度越快）
void set_stepmotor_acc(int ch,int acc);

//复位步进电机驱动器，释放电机力矩
void set_stepmotor_reset(void); 

//在带步进电机总线上的485舵机，设置舵机角度
void set_step_servoa(int id,int speed,int angle);

#endif
#endif
