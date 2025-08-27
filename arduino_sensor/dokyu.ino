#include <NimBLEDevice.h>
#include "HX711.h"

// ==================== BLE 설정 ====================
#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHARACTERISTIC_UUID "abcd1234-1234-1234-1234-abcdef123456"

NimBLEServer* pServer;
NimBLECharacteristic* pCharacteristic;

// ==================== HX711 설정 ====================
#define DT  4   // HX711 DOUT
#define SCK 5   // HX711 CLK
HX711 scale;
float calibration_factor = 22.0;  // 보정 계수
float weightThreshold = 5000.0;   // 5000g 이상일 때 신호 전송

// HX711 안정화 시간(ms)
const int HX711_STABILIZE = 3000;

// notify 간격(ms)
unsigned long lastNotifyTime = 0;
const unsigned long notifyInterval = 2000; // 2초마다 notify

void setup() {
    Serial.begin(115200);

    // --- HX711 초기화 ---
    scale.begin(DT, SCK);
    Serial.println("=== HX711 Loadcell Test ===");
    Serial.println("Step 1: Remove all weight from scale.");

    // HX711 안정화
    delay(HX711_STABILIZE);

    // tare
    scale.tare(15);
    Serial.println("Tare done! Zero point set.");

    // --- BLE 초기화 ---
    NimBLEDevice::init("ESP32_Loadcell");  // BLE 이름 설정
    pServer = NimBLEDevice::createServer();

    NimBLEService* pService = pServer->createService(SERVICE_UUID);
    pCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );

    pService->start();

    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setName("ESP32_Loadcell");    // BLE 광고 이름
    pAdvertising->start();

    Serial.println("BLE server started, waiting for connection...");

    // BLE 광고 안정화 시간
    delay(2000);
}

void loop() {
    // HX711 데이터 준비 확인
    if (!scale.is_ready()) {
        Serial.println("HX711 not ready");
        delay(100);
        return;
    }

    // 무게 측정
    float weight = scale.get_units(10) / calibration_factor;
    Serial.print("Weight: ");
    Serial.print(weight, 2);
    Serial.println(" g");

    // 무게가 임계값 이상일 때 BLE로 신호 전송
    if (weight >= weightThreshold) {
        unsigned long now = millis();
        if (now - lastNotifyTime > notifyInterval) {
            Serial.println("Weight threshold exceeded, sending BLE signal...");
            pCharacteristic->setValue("WEIGHT_EXCEEDED");
            pCharacteristic->notify();
            lastNotifyTime = now; // 마지막 notify 시간 기록
        }
    }

    delay(200); // 샘플링 간격
}
