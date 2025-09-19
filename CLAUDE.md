# KimsAutoTrade Telegram Bot - Claude Development Guide

You are an expert in Telegram bot development with 30+ years of experience. You know everything about how to create high-quality, production-ready code that doesn't need debugging. You understand bot architecture, user experience flows, API integrations, database design, and deployment patterns.

## Project Overview

This is a **KimsAutoTrade Telegram bot** that calculates car import costs from South Korea to three countries: Russia (🇷🇺), Kazakhstan (🇰🇿), and Kyrgyzstan (🇰🇬). The bot scrapes car data from Korean automotive websites and provides detailed cost breakdowns including customs fees, taxes, logistics, and total expenses.

### Core Business Logic

- **Car Data Scraping**: Extracts vehicle information from encar.com and kimsautotrade.com URLs
- **Multi-Country Calculations**: Different tax rates, customs fees, and currency conversions for each destination
- **Real-Time Currency Rates**: Integrates with multiple APIs (CBR, NBK, NBKR, USDT exchanges)
- **Cost Breakdown**: Detailed calculations including purchase price, customs, logistics, insurance, and final costs

## Project Structure

```
kimsautotrade-telegram-bot/
├── main.py                    # Main bot entry point and message handlers
├── calculator.py              # Core calculation logic and country-specific handlers
├── config.py                  # Bot configuration and token setup
├── utils.py                   # Utility functions, formatting, customs calculations
├── get_car_info.py           # Web scraping functions for car data extraction
├── get_insurance_total.py    # Insurance calculation utilities
├── kgs_customs_table.py      # Kyrgyzstan customs fee lookup tables
├── requirements.txt          # Python dependencies
├── Procfile                  # Heroku deployment configuration
├── runtime.txt               # Python version specification
└── notes.txt                 # Business notes and calculation references
```

## Architecture & Design Patterns

### Bot Structure

- **Message Handlers**: Function-based handlers using `@bot.message_handler` decorators
- **Callback Queries**: Inline keyboard interactions for user selections
- **State Management**: Global variables and user data dictionaries for session state
- **Error Handling**: Try-catch blocks with user-friendly error messages

### Database Design

**PostgreSQL Schema (car_info table)**:

```sql
CREATE TABLE car_info (
    car_id VARCHAR,
    date VARCHAR,           -- Format: DDMMYY (e.g., "010521")
    engine_volume INTEGER,  -- Engine displacement in cm³
    price INTEGER,          -- Price in Korean Won (KRW)
    car_type VARCHAR        -- "sedan" or "crossover"
);
```

**Unique Constraint**: `(date, engine_volume, price)` - prevents duplicate entries

### API Integrations

#### Currency Rate APIs

1. **CBR (Central Bank of Russia)**: `get_currency_rates()` - USD/EUR to RUB
2. **NBK (National Bank of Kazakhstan)**: `get_nbk_currency_rates()` - USD/KRW to KZT
3. **NBKR (National Bank of Kyrgyzstan)**: `get_nbkr_currency_rates()` - USD/KRW to KGS
4. **USDT Exchanges**:
   - `get_usdt_to_krw_rate_bithumb()` - USDT to KRW via Bithumb API
   - `get_usdt_to_rub_rate()` - USDT to RUB via Coinbase API

#### External Services

- **calcus.ru**: Russian customs fee calculations via POST API
- **Selenium WebDriver**: Car data scraping from Korean websites
- **encar.com**: Primary car listing source
- **kimsautotrade.com**: Secondary car listing source

## Code Standards & Conventions

### Variable Naming

- `user_data`: Global dictionary for storing user session data
- `current_country`: Active calculation country ("Russia", "Kazakhstan", "Kyrgyzstan")
- `car_data`: Global dictionary for extracted car information
- Rate variables: `usd_rate_kz`, `krw_rate_kz`, `usd_rub_rate`, etc.

### Function Patterns

```python
# Country-specific calculation functions
def calculate_cost(chat_id, country, car_type, car_data)
def calculate_cost_manual(chat_id, country, car_type, manual_data)

# Currency rate fetching
def get_currency_rates()  # CBR rates
def get_nbk_currency_rates()  # Kazakhstan rates
def get_nbkr_currency_rates()  # Kyrgyzstan rates

# Utility functions
def format_number(number)  # Format numbers with thousand separators
def calculate_age(year, month)  # Calculate car age for customs
def clean_number(value)  # Remove spaces and convert to number
```

### Error Handling Patterns

```python
try:
    # Database operations
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
except psycopg2.Error as e:
    print(f"Database error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
```

### Message Handler Patterns

```python
@bot.message_handler(commands=["start"])
def start(message):
    # Initialize user session
    # Send welcome message with reply keyboard

@bot.message_handler(func=lambda message: message.text == "Specific Text")
def handle_specific_action(message):
    # Handle specific button presses

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    # Handle inline keyboard callbacks
```

## Key Components

### 1. Main Bot Logic (`main.py`)

- **Entry Point**: Bot token initialization and command setup
- **Command Handlers**: `/start`, `/cbr`, `/nbk`, `/nbkr` commands
- **Country Selection**: Russia, Kazakhstan, Kyrgyzstan flow handlers
- **URL Processing**: Handles encar.com and kimsautotrade.com links
- **Contact Handlers**: Instagram, WhatsApp, Telegram channel integration

### 2. Calculation Engine (`calculator.py`)

- **Core Logic**: `calculate_cost()` and `calculate_cost_manual()`
- **Currency Conversion**: Real-time rate fetching and conversion
- **Customs Calculations**: Country-specific tax and fee calculations
- **Result Formatting**: Detailed cost breakdown messages
- **Database Operations**: Car data storage and retrieval

### 3. Web Scraping (`get_car_info.py`)

- **Selenium Driver**: Chrome WebDriver with proxy support
- **Data Extraction**: Price, engine volume, manufacture date, car type
- **Captcha Handling**: 2captcha integration (currently disabled)
- **Data Validation**: Format conversion and cleaning

### 4. Utilities (`utils.py`)

- **Rate Limiting**: API request throttling for calcus.ru
- **Number Formatting**: Locale-aware thousand separators
- **Customs Calculations**: Russia-specific customs fee API integration
- **Age Calculation**: Car age determination for tax brackets

### 5. Country-Specific Data (`kgs_customs_table.py`)

- **Kyrgyzstan Customs**: Static fee tables by year and engine volume
- **Tax Brackets**: Different rates based on car age and specifications

## User Experience Flow

### 1. Bot Initialization

```
/start → Country Selection (🇷🇺🇰🇿🇰🇬) → Calculation Method → Results
```

### 2. Calculation Methods

- **URL Input**: Paste encar.com or kimsautotrade.com link
- **Manual Input**: Enter car details manually
- **Link Processing**: Automatic data extraction and calculation

### 3. Result Display

- **Cost Breakdown**: Purchase price, customs, logistics, total
- **Currency Display**: Multiple currency formats (KRW, USD, local currency)
- **Action Buttons**: Calculate another car, contact manager, technical report

## Environment Configuration

### Required Environment Variables

```bash
BOT_TOKEN=your_telegram_bot_token
CHROMEDRIVER_PATH_LOCAL=/path/to/chromedriver
DATABASE_URL=postgresql://user:pass@host:port/db
```

### Heroku Deployment

- **Procfile**: `worker: python main.py`
- **Runtime**: Python 3.13
- **Dependencies**: See `requirements.txt`

## Testing Guidelines

### Manual Testing Checklist

1. **Bot Commands**: Test `/start`, `/cbr`, `/nbk`, `/nbkr`
2. **Country Selection**: Verify all three country flows
3. **URL Processing**: Test with valid encar.com links
4. **Manual Calculation**: Test manual data entry
5. **Currency Rates**: Verify real-time rate fetching
6. **Database**: Test car data storage and retrieval
7. **Error Handling**: Test invalid URLs and network errors

### Test Data

- **Valid encar.com URL**: `https://www.encar.com/dc/dc_cardetailview.do?carid=123456`
- **Test Car Data**: Price: 15000000 KRW, Engine: 2000cc, Year: 2020

## Development Best Practices

### Code Quality

- **No Global State Pollution**: Use function parameters instead of globals where possible
- **Error Recovery**: Always provide fallback values for API failures
- **User Feedback**: Clear error messages in Russian/local language
- **Memory Management**: Call `clear_memory()` after heavy operations

### Security Considerations

- **Environment Variables**: Never commit sensitive tokens or URLs
- **Database Connections**: Always use SSL mode for PostgreSQL
- **API Rate Limits**: Respect external API rate limits
- **Input Validation**: Sanitize all user inputs before processing

### Performance Optimization

- **Database Connection Pooling**: Minimize connection overhead
- **API Caching**: Cache currency rates to reduce API calls
- **Selenium Optimization**: Reuse WebDriver instances when possible
- **Memory Cleanup**: Explicit garbage collection after scraping

## Common Development Tasks

### Adding a New Country

1. Add country button in `show_country_selection()`
2. Create country-specific handler in `main.py`
3. Implement calculation logic in `calculator.py`
4. Add currency rate fetching if needed
5. Update customs calculation logic

### Adding New Car Data Sources

1. Create new scraping function in `get_car_info.py`
2. Update URL pattern matching in `main.py`
3. Add data extraction and formatting logic
4. Test with multiple car listings

### Updating Currency APIs

1. Modify rate fetching functions in `calculator.py`
2. Update error handling for API failures
3. Test rate conversion accuracy
4. Update rate display formatting

## Debugging & Monitoring

### Common Issues

- **WebDriver Failures**: Check ChromeDriver version compatibility
- **Database Errors**: Verify PostgreSQL connection and SSL requirements
- **API Rate Limits**: Monitor calcus.ru request frequency
- **Currency API Failures**: Implement fallback rate sources

### Logging Patterns

```python
print(f"Error message: {error}")  # Console logging
bot.send_message(chat_id, "User-friendly error message")  # User notification
```

## Production Considerations

### Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] ChromeDriver version compatible
- [ ] API rate limits configured
- [ ] Error monitoring enabled
- [ ] Bot commands registered

### Monitoring

- **Database Performance**: Monitor query execution times
- **API Response Times**: Track external API latency
- **Error Rates**: Monitor bot error frequency
- **User Activity**: Track calculation requests per country

Remember: This bot handles financial calculations, so accuracy is critical. Always verify calculation logic against known test cases and provide clear cost breakdowns to users.
