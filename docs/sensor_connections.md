# Connections Overview for Raspberry Pi 3 A+ Setup

## **Motor Controller (L298N) Connections**

### **Connections to the Raspberry Pi 3 A+**
| **L298N Pin**  | **Raspberry Pi GPIO Pin** | **Description**                                  |
|----------------|---------------------------|--------------------------------------------------|
| ENA           | GPIO 18 (Pin 12)          | PWM control for Motor 1 speed                  |
| IN1           | GPIO 23 (Pin 16)          | Control signal for Motor 1 (direction)         |
| IN2           | GPIO 24 (Pin 18)          | Control signal for Motor 1 (direction)         |
| ENB           | GPIO 17 (Pin 11)          | PWM control for Motor 2 speed                  |
| IN3           | GPIO 22 (Pin 15)          | Control signal for Motor 2 (direction)         |
| IN4           | GPIO 27 (Pin 13)          | Control signal for Motor 2 (direction)         |

### **Power Connections**
| **L298N Pin**  | **Connection**                          | **Description**                      |
|----------------|-----------------------------------------|--------------------------------------|
| 12V            | 12V Power Supply (+)                   | External power source for motors     |
| GND            | Power Supply (-) and Pi GND (Pin 6)    | Common ground for Pi and motors      |
| 5V             | Not connected (powered via micro USB)  | Optional 5V output from L298N        |

### **Motor Outputs**
| **L298N Pin**  | **Connection**          | **Description**          |
|----------------|-------------------------|--------------------------|
| OUT1, OUT2     | Motor 1 terminals       | Connect to Motor 1       |
| OUT3, OUT4     | Motor 2 terminals       | Connect to Motor 2       |

---

## **BNO055 Sensor Connections**

### **Connections to the Raspberry Pi 3 A+**
| **BNO055 Pin** | **Raspberry Pi GPIO Pin** | **Description**                                |
|----------------|---------------------------|------------------------------------------------|
| VIN            | 3.3V (Pin 1)             | Power supply for the sensor                   |
| GND            | GND (Pin 9)              | Ground connection                             |
| SDA            | GPIO 2 (Pin 3)           | I2C Data Line                                 |
| SCL            | GPIO 3 (Pin 5)           | I2C Clock Line                                |
| INT            | Not connected            | Optional Interrupt Pin                        |

---

## **Touchscreen Connections**

### **Connections to the Raspberry Pi 3 A+**
| **Touchscreen Pin** | **Raspberry Pi GPIO Pin** | **Description**                                |
|---------------------|---------------------------|------------------------------------------------|
| 5V                 | Pin 2                    | Power supply for the touchscreen              |
| GND                | Pin 7                    | Ground connection                             |
| SDA                | GPIO 2 (Pin 3)           | Shared I2C Data Line with BNO055              |
| SCL                | GPIO 3 (Pin 5)           | Shared I2C Clock Line with BNO055             |
| INT                | GPIO 14 (Pin 8)          | Interrupt pin for the touchscreen             |

---

## **Power Supply Notes**
1. The Raspberry Pi is powered via a micro USB power adapter.
2. The L298N is powered by a 12V 2A external power supply.
3. Common ground is established between the Raspberry Pi and L298N.

---

## **Connection Diagram**
### Motor Controller:
```
Raspberry Pi GPIO (PWM, Direction) ---> L298N ---> Motors
12V Power Supply (+/-) -------------> L298N Power Pins
```
### BNO055:
```
Raspberry Pi GPIO (SDA, SCL, 3.3V, GND) ---> BNO055 Sensor
```
### Touchscreen:
```
Raspberry Pi GPIO (5V, GND, SDA, SCL, INT) ---> Touchscreen Module
```

---

## **References**
1. L298N Motor Driver Datasheet
2. BNO055 Sensor Datasheet
3. Raspberry Pi GPIO Pinout: [https://pinout.xyz](https://pinout.xyz)