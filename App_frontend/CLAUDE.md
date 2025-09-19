# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MikeApp is an Android business card scanning and management application. It combines camera-based OCR functionality with a comprehensive business card database system. The app supports both Chinese and English text recognition and can work both online (with backend API) and offline (local-only mode).

## Development Commands

### Build and Development
```bash
# Build the project
./gradlew build

# Clean build
./gradlew clean

# Build debug APK
./gradlew assembleDebug

# Build release APK
./gradlew assembleRelease

# Install debug build on connected device
./gradlew installDebug
```

### Testing
```bash
# Run unit tests
./gradlew test

# Run instrumented tests (requires connected device/emulator)
./gradlew connectedAndroidTest

# Run specific test class
./gradlew test --tests "com.mike.mikeapp.ExampleUnitTest"
```

### Code Quality
```bash
# Lint check
./gradlew lint

# Generate lint report
./gradlew lintDebug
```

## Architecture Overview

### Core Components

**Data Layer:**
- `Card` (model): Comprehensive business card entity with 25 standardized fields supporting Chinese/English bilingual data
- `CardDao`: Room database access object for local storage operations
- `CardDatabase`: Room database configuration with migration support
- `CardRepository`: Single source of truth that coordinates between local database and remote API

**UI Layer:**
- `MainActivity`: Main dashboard with statistics and navigation
- `ScanActivity`: Camera-based card scanning with CameraX integration
- `CardListActivity`: Card management with search and filtering
- `AddCardActivity`: Manual card entry form
- `CardDetailActivity`: Individual card viewing and editing

**Network Layer:**
- `ApiService`: Retrofit interface defining all backend endpoints
- `ApiClient`: Singleton HTTP client configuration with OkHttp
- `OcrService`: Handles image upload and OCR processing via backend API

**Key Features:**
- **Hybrid Architecture**: Seamlessly works online with backend sync or offline with local data only
- **Bilingual Support**: All card fields support both Chinese (Zh) and English (En) variants
- **Health Status**: Cards are automatically classified as "normal" or "incomplete" based on field completeness
- **Camera Integration**: CameraX implementation for high-quality card image capture
- **Permission Management**: Runtime permission handling for camera and storage access

### Data Model Structure

The `Card` entity follows a standardized 25-field structure:
- **Basic Info** (8 fields): Names, company names, positions (primary + secondary)
- **Organization** (6 fields): Department hierarchy (3 levels, bilingual)
- **Contact Info** (5 fields): Mobile, company phones, email, Line ID
- **Address Info** (4 fields): Company addresses (2 locations, bilingual)
- **Notes** (2 fields): Custom notes for additional information

### Repository Pattern

`CardRepository` implements a sophisticated data synchronization strategy:
1. Attempts server operations first when online
2. Falls back to local database operations when offline
3. Automatically syncs local changes when connection is restored
4. Provides unified callback interface for UI components

## Key Libraries and Dependencies

- **CameraX**: Modern camera API for image capture
- **Room**: Local SQLite database with type-safe queries
- **Retrofit + OkHttp**: REST API communication with logging
- **Gson**: JSON serialization/deserialization
- **Glide**: Image loading and caching
- **Material Design**: UI components following Material Design guidelines

## Development Notes

- Package structure follows feature-based organization under `com.mike.mikeapp`
- All database operations are asynchronous using background threads
- API responses follow standardized `ApiResponse<T>` wrapper format
- ViewBinding is enabled for type-safe view access
- Target SDK is 36 with minimum SDK 24
- Java 11 source/target compatibility