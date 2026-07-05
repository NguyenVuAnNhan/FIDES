plugins {
    kotlin("android") version "1.9.24"
}

group = "ai.fides"
version = "0.1.0"

android {
    namespace = "ai.fides.sdk"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }
}

