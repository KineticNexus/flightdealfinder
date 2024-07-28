# Flight Deal Finder

This Python project searches for flight deals using the SerpAPI (Google Flights data) and sends notifications about the best deals via Twilio WhatsApp.

## Features

- Searches for flight deals from multiple origin cities to various destinations
- Uses SerpAPI free API (only 100 free searches per month) to fetch real-time flight data from Google Flights
- Implements an optimization algorithm to find the best deals within given parameters
- Sends WhatsApp notifications for new lowest price alerts using Twilio
- Stores and updates destination data in an Excel file
- Comprehensive logging for debugging and monitoring

## Requirements

- Python 3.x
- pandas
- requests
- twilio
- python-dotenv

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/flight-deal-finder.git
   ```
2. Install the required packages:
   ```
   pip install pandas requests twilio python-dotenv
   ```
3. Set up a `.env` file in the project root with the following variables:
   ```
   SERPAPI_API_KEY=your_serpapi_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_WHATSAPP_NUMBER=your_twilio_whatsapp_number
   YOUR_WHATSAPP_NUMBER=your_personal_whatsapp_number
   ```

## Usage

Run the script using Python:

```
python flight_deal_finder.py
```

The script will:
1. Load or create a list of destinations
2. Search for flights from specified origin cities to each destination
3. Optimize the search based on trip duration and date range
4. Update the Excel file with new lowest prices
5. Send WhatsApp notifications for new deals

## How it Works

1. The `FlightDealFinder` class manages the overall process:
   - Loads destination data from an Excel file
   - Uses SerpAPI to fetch flight data
   - Implements an optimization algorithm to find the best deals
   - Updates the Excel file with new data
   - Triggers notifications for new deals

2. The `NotificationManager` class handles WhatsApp notifications using Twilio.

3. The script uses environment variables for API keys and sensitive data.

4. Logging is implemented throughout the script for debugging and monitoring.

## Customization

You can adjust the following parameters in the script:
- `MIN_MAX_TRIP_DURATION`: Range of trip durations to search
- `MIN_MAX_SEARCH_PERIOD`: Range of days from today to search for flights
- `MAX_ITERATIONS`: Maximum number of iterations for the search algorithm per departure airport
- Origin cities in the `origin_city_iatas` list

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
