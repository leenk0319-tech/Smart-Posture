#include <NimBLEDevice.h>
#include "HX711.h"

// ==================== BLE 설정 ====================
#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHARACTERISTIC_UUID "abcd1234-1234-1234-1234-abcdef123456"

NimBLEServer* pServer;
NimBLECharacteristic* pCharacteristic;

// ==================== HX711 설정 ====================
#define DT1  4   // 좌측 센서 DOUT
#define SCK1 5   // 좌측 센서 CLK
#define DT2  18  // 우측 센서 DOUT
#define SCK2 19  // 우측 센서 CLK

HX711 scaleL;
HX711 scaleR;

float calibration_factor = 22.0;           // 보정 계수
float imbalanceThresholdRatio = 0.1;       // 체중 대비 10% 이상 차이면 불균형

// ==================== SETUP ====================
void setup() {
  Serial.begin(115200);

  // --- 좌측 센서 초기화 ---
  scaleL.begin(DT1, SCK1);
  delay(500);
  Serial.println("Initializing Left Sensor...");
  delay(2000);
  scaleL.tare(15);
  Serial.println("Left Sensor Tare done!");

  // --- 우측 센서 초기화 ---
  scaleR.begin(DT2, SCK2);
  delay(500);
  Serial.println("Initializing Right Sensor...");
  delay(2000);
  scaleR.tare(15);
  Serial.println("Right Sensor Tare done!");

  // --- BLE 초기화 ---
  NimBLEDevice::init("ESP32_Balance");  // BLE 이름 설정
  pServer = NimBLEDevice::createServer();

  NimBLEService* pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      NIMBLE_PROPERTY::NOTIFY
                    );

  pService->start();

  // --- 광고 설정 및 간격 최소화 ---
  NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setName("ESP32_Balance");    // BLE 광고 이름

  // 광고 간격 최소화: 30~40ms
  pAdvertising->setMinInterval(0x20); // 0x20 * 0.625ms = 32ms
  pAdvertising->setMaxInterval(0x40); // 0x40 * 0.625ms = 64ms

  pAdvertising->start();

  Serial.println("BLE server started, waiting for connection...");
}

// ==================== LOOP ====================
void loop() {
  delay(200);

  // --- 센서 준비 확인 ---
  if (!scaleL.is_ready() || !scaleR.is_ready()) {
    Serial.println("One of the HX711 sensors is not ready");
    delay(100);
    return;
  }

  // --- 무게 측정 ---
  float weightL = scaleL.get_units(10) / calibration_factor;
  float weightR = scaleR.get_units(10) / calibration_factor;

  if (weightL < 0) weightL = 0;
  if (weightR < 0) weightR = 0;

  float totalWeight = weightL + weightR;
  float diff = abs(weightL - weightR);
  float diffRatio = (totalWeight > 0) ? diff / totalWeight : 0;  // 0으로 나누기 방지

  // --- 센서 무게 출력 ---
  Serial.print("Left Weight: ");
  Serial.print(weightL, 2);
  Serial.print(" g   |   Right Weight: ");
  Serial.print(weightR, 2);
  Serial.print(" g   |   Difference Ratio: ");
  Serial.println(diffRatio, 2);

  // --- 균형 / 불균형 감지 ---
  if (diffRatio >= imbalanceThresholdRatio) {
    if (weightL > weightR) {
      Serial.println("Left side heavier → LEFT");
      pCharacteristic->setValue("LEFT");
      pCharacteristic->notify();
    } else {
      Serial.println("Right side heavier → RIGHT");
      pCharacteristic->setValue("RIGHT");
      pCharacteristic->notify();
    }
  } else {
    Serial.println("Balanced → BALANCED");
    pCharacteristic->setValue("BALANCED");
    pCharacteristic->notify();
  }

  delay(500); // 샘플링 간격
}
