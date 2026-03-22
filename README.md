# Weather App

A locally hosted web app that fetches and displays weather data from a public REST API.

## Overview

This app ingests data from a public weather REST API and presents it through a local web interface.

## Getting Started

### Prerequisites

- Node.js (or your chosen runtime)
- API key from your weather data provider

### Installation

1. Clone the repository
2. Install dependencies
3. Configure your API key (see [Configuration](#configuration))
4. Start the local server

### Configuration

Copy the example environment file and add your API credentials:

```bash
cp .env.example .env
```

Set your API key in `.env`:

```
WEATHER_API_KEY=your_api_key_here
```

### Running the App

```bash
npm start
```

Then open your browser to `http://localhost:3000` (or the configured port).

## Features

- Fetches current weather data from a public REST API
- Displays weather information in a local web interface

## API

This project uses a public weather REST API. Popular options:
- [Open-Meteo](https://open-meteo.com/) — free, no API key required
- [OpenWeatherMap](https://openweathermap.org/api) — free tier available
- [WeatherAPI](https://www.weatherapi.com/) — free tier available
