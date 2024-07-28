import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException
import random
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hyperparameters
MIN_MAX_TRIP_DURATION = (7, 10)  # Min and max number of days for the trip
MIN_MAX_SEARCH_PERIOD = (150, 180)  # Min and max number of days from today to search for flights
MAX_ITERATIONS = 3  # Maximum number of iterations for  search algorithm per departure airport

class NotificationManager:
    def __init__(self):
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
        self.to_whatsapp_number = os.getenv("YOUR_WHATSAPP_NUMBER")

        logger.debug(f"TWILIO_ACCOUNT_SID: {'*' * len(self.twilio_sid) if self.twilio_sid else 'Not set'}")
        logger.debug(f"TWILIO_AUTH_TOKEN: {'*' * len(self.twilio_token) if self.twilio_token else 'Not set'}")
        logger.debug(f"TWILIO_WHATSAPP_NUMBER: {self.from_whatsapp_number}")
        logger.debug(f"YOUR_WHATSAPP_NUMBER: {self.to_whatsapp_number}")

        self.client = None
        if self.twilio_sid and self.twilio_token:
            try:
                self.client = TwilioClient(self.twilio_sid, self.twilio_token)
                # Test the client by fetching the account details
                account = self.client.api.accounts(self.twilio_sid).fetch()
                logger.info(f"Twilio client created successfully. Account status: {account.status}")
            except TwilioRestException as e:
                logger.error(f"Twilio API error: {e}")
            except Exception as e:
                logger.error(f"Failed to create Twilio client: {str(e)}")
        else:
            logger.warning("Twilio credentials not set. Notifications will not be sent.")

    def send_whatsapp(self, message):
        if not self.client:
            logger.warning("Twilio client not initialized. Message not sent.")
            return

        if not all([self.from_whatsapp_number, self.to_whatsapp_number]):
            logger.warning("WhatsApp numbers not set. Message not sent.")
            return

        try:
            message = self.client.messages.create(
                body=message,
                from_=f"whatsapp:{self.from_whatsapp_number}",
                to=f"whatsapp:{self.to_whatsapp_number}"
            )
            logger.info(f"WhatsApp message sent: {message.sid}")
        except TwilioRestException as e:
            logger.error(f"Twilio API error when sending message: {e}")
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")

class FlightDealFinder:
    def __init__(self, file_path='flight_data.xlsx'):
        self.file_path = file_path
        self.destination_data = self.get_destination_data()
        self.serpapi_key = os.getenv('SERPAPI_API_KEY')
        logger.info(f"SERPAPI_API_KEY: {'Set' if self.serpapi_key else 'Not set'}")
        self.notification_manager = NotificationManager()

    def get_destination_data(self):
        if os.path.exists(self.file_path):
            df = pd.read_excel(self.file_path)
            return df.to_dict('records')
        else:
            return []

    def update_destination_data(self):
        df = pd.DataFrame(self.destination_data)
        df.to_excel(self.file_path, index=False)
        logger.info(f"Data updated and saved to {self.file_path}")

    def add_destination(self, city, iata_code="", lowest_price=float('inf')):
        new_destination = {
            "city": city,
            "iataCode": iata_code,
            "lowestPrice": lowest_price,
            "departureCity": "",
            "departureAirport": "",
            "arrivalCity": "",
            "arrivalAirport": "",
            "flightCodeOutbound": "",
            "flightCodeInbound": "",
            "departureDate": "",
            "returnDate": "",
            "tripDuration": "",
            "stopoversOutbound": "",
            "stopoversInbound": "",
            "flightTimeOutbound": "",
            "flightTimeInbound": "",
            "outboundPrice": "",
            "inboundPrice": ""
        }
        self.destination_data.append(new_destination)
        self.update_destination_data()

    def check_flights(self, origin_city_code, destination_city_code, departure_date, return_date):
        try:
            params = {
                "engine": "google_flights",
                "departure_id": origin_city_code,
                "arrival_id": destination_city_code,
                "outbound_date": departure_date.strftime("%Y-%m-%d"),
                "return_date": return_date.strftime("%Y-%m-%d"),
                "currency": "USD",
                "hl": "en",
                "api_key": self.serpapi_key
            }
            
            response = requests.get("https://serpapi.com/search", params=params)
            data = response.json()
            
            if "error" in data:
                logger.warning(f"API error for {origin_city_code} to {destination_city_code} on {departure_date}: {data['error']}")
                return None
            
            flights = data.get("best_flights", []) + data.get("other_flights", [])
            
            if not flights:
                logger.info(f"No flights found for {origin_city_code} to {destination_city_code} on {departure_date}")
                return None

            best_flight = min(flights, key=lambda x: x['price'])
            
            price_insights = data.get("price_insights", {})
            
            outbound = best_flight['flights'][0]
            inbound = best_flight['flights'][-1]
            
            return {
                "total_price": best_flight['price'],
                "outbound_price": None,  # API doesn't provide separate prices
                "inbound_price": None,   # API doesn't provide separate prices
                "origin_city": origin_city_code,
                "origin_airport": outbound['departure_airport']['id'],
                "destination_city": destination_city_code,
                "destination_airport": inbound['arrival_airport']['id'],
                "out_date": departure_date.strftime("%Y-%m-%d"),
                "return_date": return_date.strftime("%Y-%m-%d"),
                "trip_duration": (return_date - departure_date).days,
                "flight_code_outbound": outbound['flight_number'],
                "flight_code_inbound": inbound['flight_number'],
                "stopovers_outbound": len(best_flight['flights']) // 2 - 1,
                "stopovers_inbound": len(best_flight['flights']) // 2 - 1,
                "flight_time_outbound": outbound['duration'],
                "flight_time_inbound": inbound['duration'],
                "lowest_price": price_insights.get("lowest_price"),
                "price_level": price_insights.get("price_level"),
                "typical_price_range": price_insights.get("typical_price_range"),
                "outbound_departure_time": outbound['departure_airport']['time'],
                "outbound_arrival_time": outbound['arrival_airport']['time'],
                "inbound_departure_time": inbound['departure_airport']['time'],
                "inbound_arrival_time": inbound['arrival_airport']['time'],
                "outbound_airline": outbound['airline'],
                "inbound_airline": inbound['airline']
            }
        except Exception as error:
            logger.error(f"Error checking flight: {error}")
            return None

    def optimize_search(self, origin_city_code, destination_city_code, start_date):
        best_flight = None
        lowest_price = float('inf')

        for _ in range(MAX_ITERATIONS):
            trip_duration = random.randint(MIN_MAX_TRIP_DURATION[0], MIN_MAX_TRIP_DURATION[1])
            days_from_start = random.randint(0, MIN_MAX_SEARCH_PERIOD[1] - trip_duration)
            departure_date = start_date + timedelta(days=days_from_start)
            return_date = departure_date + timedelta(days=trip_duration)

            current_flight = self.check_flights(
                origin_city_code,
                destination_city_code,
                departure_date,
                return_date
            )

            if current_flight:
                current_price = current_flight['total_price']
                if current_price < lowest_price:
                    best_flight = current_flight
                    lowest_price = current_price

                # If we find a price that's within the typical range or lower, we can stop searching
                if current_flight['typical_price_range'] and current_price <= current_flight['typical_price_range'][1]:
                    break

        return best_flight

    def run(self):
        if not self.destination_data:
            destinations = [
                ("Paris", "CDG"), ("Berlin", "BER"), ("Tokyo", "HND"),
                ("Sydney", "SYD"), ("Istanbul", "IST"), ("Kuala Lumpur", "KUL"),
                ("New York", "JFK"), ("San Francisco", "SFO"), ("Cape Town", "CPT"),
                ("Rio de Janeiro", "GIG"), ("Lima", "LIM"), ("Cancun", "CUN"),
                ("Dubai", "DXB"), ("Bangkok", "BKK"), ("Rome", "FCO"),
                ("Barcelona", "BCN"), ("Amsterdam", "AMS"), ("Prague", "PRG"),
                ("Vienna", "VIE"), ("Athens", "ATH")
            ]
            for city, code in destinations:
                self.add_destination(city, code)

        self.update_destination_data()

        start_date = datetime.now() + timedelta(days=1)

        origin_city_iatas = ["ASU"]  #["BUE", "SAO", "ASU"]  # Buenos Aires, Sao Paulo, Asuncion

        for origin_city_iata in origin_city_iatas:
            for destination in self.destination_data:
                try:
                    flight = self.optimize_search(
                        origin_city_iata,
                        destination["iataCode"],
                        start_date
                    )
                    
                    if flight is None:
                        continue

                    current_lowest_price = destination["lowestPrice"]
                    if flight["total_price"] < current_lowest_price:
                        destination.update({
                            "lowestPrice": flight["total_price"],
                            "outboundPrice": flight["outbound_price"],
                            "inboundPrice": flight["inbound_price"],
                            "departureCity": flight["origin_city"],
                            "departureAirport": flight["origin_airport"],
                            "arrivalCity": flight["destination_city"],
                            "arrivalAirport": flight["destination_airport"],
                            "flightCodeOutbound": flight["flight_code_outbound"],
                            "flightCodeInbound": flight["flight_code_inbound"],
                            "departureDate": flight["out_date"],
                            "returnDate": flight["return_date"],
                            "tripDuration": flight["trip_duration"],
                            "stopoversOutbound": flight["stopovers_outbound"],
                            "stopoversInbound": flight["stopovers_inbound"],
                            "flightTimeOutbound": flight["flight_time_outbound"],
                            "flightTimeInbound": flight["flight_time_inbound"]
                        })
                        
                        self.update_destination_data()
                        
                        message = (
                            f"Low price alert! Only ${flight['total_price']} for a {flight['trip_duration']}-day round trip from "
                            f"{flight['origin_city']}-{flight['origin_airport']} to "
                            f"{flight['destination_city']}-{flight['destination_airport']}.\n"
                            f"Outbound Flight: {flight['outbound_airline']} {flight['flight_code_outbound']}\n"
                            f"Departure: {flight['out_date']} at {flight['outbound_departure_time']}, "
                            f"Arrival: {flight['outbound_arrival_time']}\n"
                            f"Stopovers: {flight['stopovers_outbound']}, Duration: {flight['flight_time_outbound'] // 60} hours {flight['flight_time_outbound'] % 60} minutes\n"
                            f"Return Flight: {flight['inbound_airline']} {flight['flight_code_inbound']}\n"
                            f"Departure: {flight['return_date']} at {flight['inbound_departure_time']}, "
                            f"Arrival: {flight['inbound_arrival_time']}\n"
                            f"Stopovers: {flight['stopovers_inbound']}, Duration: {flight['flight_time_inbound'] // 60} hours {flight['flight_time_inbound'] % 60} minutes\n"
                            f"This price is for the entire round trip.\n"
                        )
                        if current_lowest_price != float('inf'):
                            message += f"This is lower than the previous lowest price of ${current_lowest_price:.2f}.\n"
                        else:
                            message += "This is the first recorded price for this route.\n"
                        
                        if flight['price_level']:
                            message += f"Price level: {flight['price_level']}\n"
                        if flight['typical_price_range']:
                            message += f"Typical price range: ${flight['typical_price_range'][0]} - ${flight['typical_price_range'][1]}"
                        
                        logger.info(message)
                        self.notification_manager.send_whatsapp(message)
                    
                except Exception as error:
                    logger.error(f"An error occurred: {error}")

if __name__ == "__main__":
    finder = FlightDealFinder()
    finder.run()
