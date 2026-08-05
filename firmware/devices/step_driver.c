#include "whalesbot.h"


#ifdef EXTERNLIB_STEPDRIVER_H_
#ifdef GCC_CODE//�˹���ֻ��GCC״̬�£��Ž��б���





#define STEP_DRIVERID  100   //���������ID��
#define STEP_REG_SPD   6     //������3�ŵ����Ӧ���ٶȼĴ������
#define STEP_DT        0.01  //ʱ����
#define STEP_SPD_MAX   32000//�������ٶ�
#define STEP_SPD_MIN   50   //�����С�ٶ�
//д���߶��
#define StepDriver_LEN      14
#define StepDriver_REVLEN   10
static uint8_t StepDriver_Buffer[StepDriver_LEN]={0};
static int StepDriverIndex=0;
static uint8_t StepDriver_RevBuffer[StepDriver_REVLEN*2]={0};


//3·���Ŀ���ٶ�
static float step_spd1=0;
static float step_spd2=0;
static float step_spd3=0;

//������������PWM����
static int step_distance1=0;
static int step_distance2=0;
static int step_distance3=0;

static float SPD_ACC_1   =1000;
static float SPD_ACC_2   =1000;
static float SPD_ACC_3   =1000;

static int isInit=false;
static int isReset=false;

static int step_spd1_now=0;
static int step_spd2_now=0;
static int step_spd3_now=0;

static int sid = 0;
static int sspeed = 0;
static int sangle = 0;

/* 485 总线独占标志 (自研扩展):
 * 非 0 时 StepMotorThread 暂停全部总线操作 (不写速度帧、不注册 RX 回调),
 * 供 485 舵机独立 API (servo_id_change 等) 独占总线使用。
 * 由 services.c 在调用前后置位/复位。 */
volatile int step_bus_busy = 0;

static int StepDriver_WriteRegister(int id, int Reg, int spd1,int spd2,int spd3)
{
    StepDriver_Buffer[0] = 0xFF;
    StepDriver_Buffer[1] = 0xFF;
    StepDriver_Buffer[2] = id;
    StepDriver_Buffer[3] = StepDriver_LEN-4;//���ͳ���
    StepDriver_Buffer[4] = 0x07;//д��ָ��
    StepDriver_Buffer[5] = Reg;
    StepDriver_Buffer[7] =  (uint8_t)((  spd1 >> 8) & 0x000000ff);
    StepDriver_Buffer[8] =  (uint8_t)(   spd1  &      0x000000ff); 
    StepDriver_Buffer[9] =  (uint8_t)((  spd2 >> 8) & 0x000000ff);
    StepDriver_Buffer[10] = (uint8_t)(   spd2  &      0x000000ff); 
    StepDriver_Buffer[11] = (uint8_t)((  spd3 >> 8) & 0x000000ff);
    StepDriver_Buffer[12] = (uint8_t)(   spd3  &      0x000000ff); 
    StepDriver_Buffer[13] = calchecksum(StepDriver_Buffer);
    UartPort485_Sendbytes(StepDriver_Buffer, StepDriver_LEN);
    return 0;
}


//д���߶��
static void PO16_angle(int id, int spd,int ang)
{
    uint8_t Buffer[11];
    Buffer[0] = 0xFF;
    Buffer[1] = 0xFF;
    Buffer[2] = id;
    Buffer[3] = 0x07;//���ͳ���
    Buffer[4] = 0x03;//д��ָ��
    Buffer[5] = 30;//ang
    Buffer[6] = (uint8_t)( ang  &      0x000000ff); 
    Buffer[7] =  (uint8_t)((ang >> 8) & 0x000000ff);
    Buffer[8] = (uint8_t)( spd  &      0x000000ff); 
    Buffer[9] =  (uint8_t)((spd >> 8) & 0x000000ff);
    Buffer[10] = calchecksum(Buffer);
    UartPort485_Sendbytes(Buffer, 11);
}



static void StepDriver_RevCallBack(uint8_t revdata)
{
    if(StepDriverIndex == 0 && revdata==0xff)
    {
        StepDriver_RevBuffer[0]=0xff;
        StepDriverIndex=StepDriverIndex+1;
    }
    else if(StepDriverIndex >=1 && StepDriver_RevBuffer[0]==0xff)
    {
        StepDriver_RevBuffer[StepDriverIndex]=revdata;
        StepDriverIndex++;
        if(StepDriverIndex>StepDriver_REVLEN)
            StepDriverIndex=0;
    }
    else
    {
        StepDriverIndex=0;
        StepDriver_RevBuffer[0]=0;
        StepDriver_RevBuffer[1]=0;
    }
}


static int accaplay(int vel_now,int vel_dis,int acc)
{
    if(vel_dis > (vel_now))
    {
        (vel_now) += acc;
        if((vel_now) > vel_dis)
            (vel_now) = vel_dis;
    }
    else if(vel_dis < (vel_now))
    {
        (vel_now) -= acc;
        if((vel_now) < vel_dis)
            (vel_now) = vel_dis;
    }
    else
    {
        (vel_now) = vel_dis;
    }
    return vel_now;
}

//���̴߳�������Ӽ��ٹ���
static void StepMotorThread()
{
    int step1=0;
    int step2=0;
    int step3=0;
    while (true)
    {
        /* 总线独占: 其他模块使用 485 时暂停步进总线操作 */
        if (step_bus_busy)
        {
            wait(STEP_DT);
            continue;
        }
        //������мӼ��ٿ���,ͨ��1
        step_spd1_now = accaplay(step_spd1_now,step_spd1,SPD_ACC_1);
        step_spd2_now = accaplay(step_spd2_now,step_spd2,SPD_ACC_2);
        step_spd3_now = accaplay(step_spd3_now,step_spd3,SPD_ACC_3);

        if(abs(step_spd1_now) < STEP_SPD_MIN)
            step1 = 0;
        else
            step1 = step_spd1_now;
        if(abs(step_spd2_now) < STEP_SPD_MIN)
            step2 = 0;   
        else
            step2 = step_spd2_now; 
        if(abs(step_spd3_now) < STEP_SPD_MIN)
            step3 = 0;      
        else
            step3 = step_spd3_now;   
        if(isReset == true)
        {
            Servo_Reset(STEP_DRIVERID);
        }
        else
        {
            StepDriver_WriteRegister(STEP_DRIVERID,STEP_REG_SPD,step1,step2,step3);
        }
        //���ý���
        StepDriverIndex=0;
        StepDriver_RevBuffer[0]=0;
        StepDriver_RevBuffer[1]=0;
        setUartPort485_RxHandle((FunType)StepDriver_RevCallBack);//���ý��ջص�����
        //�ͷ�CPU�������߳�
        wait(STEP_DT);
        //��ȡ����������������
        if( StepDriver_RevBuffer[0]==0xff && 
            StepDriver_RevBuffer[1]==0xff && 
            StepDriver_RevBuffer[2]==STEP_DRIVERID && 
            StepDriver_RevBuffer[StepDriver_REVLEN-1] == calchecksum(StepDriver_RevBuffer))
            {
                if(StepDriver_RevBuffer[4]==0x90)
                    step_distance1=StepDriver_RevBuffer[5]*0x1000000 + StepDriver_RevBuffer[6]*0x10000 + StepDriver_RevBuffer[7]*0x100+ StepDriver_RevBuffer[8];
                else if(StepDriver_RevBuffer[4]==0x91)
                    step_distance2=StepDriver_RevBuffer[5]*0x1000000 + StepDriver_RevBuffer[6]*0x10000 + StepDriver_RevBuffer[7]*0x100+ StepDriver_RevBuffer[8];
                else if(StepDriver_RevBuffer[4]==0x92)
                    step_distance3=StepDriver_RevBuffer[5]*0x1000000 + StepDriver_RevBuffer[6]*0x10000 + StepDriver_RevBuffer[7]*0x100+ StepDriver_RevBuffer[8];
            }

        if(sid > 0)
        {
            for(int i=0;i<10;i++)
            {
                StepDriverIndex=0;
                StepDriver_RevBuffer[0]=0;
                StepDriver_RevBuffer[1]=0;
                PO16_angle(sid,to_servo_speed(sspeed),angle_to_servo_value(sangle));
                wait(0.001);
                        //��ȡ����������������
                if( StepDriver_RevBuffer[0]==0xff && 
                    StepDriver_RevBuffer[1]==0xff && 
                    StepDriver_RevBuffer[2]==sid )
                {   break;}
            }
            sid=0;
        }
    }
}




void set_stepmotor(int ch,int speed)
{
    //��ʼ��
    if(isInit == false)
    {
        ThreadStart(StepMotorThread);
        wait(0.01);
        isInit=true;
    }
    speed = constrain(speed,-STEP_SPD_MAX,STEP_SPD_MAX);
    if(abs(speed)<STEP_SPD_MIN)
        speed=0;
    if(ch == STP_MOT_CH1)
    {
        step_spd1 = speed;
    }
    else if(ch== STP_MOT_CH2)
    {
        step_spd2 = speed;
    }
    else if(ch== STP_MOT_CH3)
    {
        step_spd3 = speed;
    }
}

void set_stepmotor_acc(int ch,int acc)
{
    //����Ӽ���ƽ���̶ȣ�0������ƽ����16000�����ٶ�
    acc= constrain(acc,0,STEP_SPD_MAX);
    if(ch == STP_MOT_CH1)
    {
        SPD_ACC_1 = acc;
    }
    else if(ch== STP_MOT_CH2)
    {
        SPD_ACC_2 = acc;
    }
    else if(ch== STP_MOT_CH3)
    {
        SPD_ACC_3 = acc;
    }
}

int get_stepmotor_distance(int ch)
{
    if(ch == STP_MOT_CH1)
    {
        return step_distance1;
    }
    else if(ch== STP_MOT_CH2)
    {
        return step_distance2;
    }
    else if(ch== STP_MOT_CH3)
    {
        return step_distance3;
    }
    return 0;
}



void set_stepmotor_reset()
{
    step_spd1=0;
    step_spd2=0;
    step_spd3=0;
    isReset=true;
    wait(0.1);//�ȴ���λ�෢�ͼ���
    isReset=false;
}


//�ڴ�������������ϵ�485��������ö���Ƕ�
void set_step_servoa(int id,int speed,int angle)
{
    sspeed = speed;
    sangle = angle;
    sid = id;
    while (true)
    {
        wait(0.001);
        if(sid == 0)//�ȴ��������
            break;
    }
}



#endif
#endif