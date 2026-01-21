from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivy.uix.label import Label
from kivymd.uix.button import MDFlatButton
from kivy.uix.popup import Popup
from kivy.clock import Clock
import random
import csv
import os
import pywhatkit
from plyer import gps  # For GPS functionality
from kivy.utils import platform  # To detect the platform (Android, iOS, Windows, etc.)
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.card import MDCard
import threading
import time
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import MDList
from kivy.metrics import dp
import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse


# Set window size
Window.size = (360, 600)

# File paths
DATA_FILE = os.path.join(os.path.dirname(__file__), "signup_data.csv")
OTP_FILE = os.path.join(os.path.dirname(__file__), "otp_data.txt")

# Thresholds for detecting an accident
GYRO_THRESHOLD = 5.0  # degrees/second
ACCEL_THRESHOLD = 5.0
MOCK_GPS_COORDINATES = {'latitude': 40.7128, 'longitude': -74.0060}

# Global variables
accident_prompt_shown = False
accident_loop_exit = False
location_sent = False  # To ensure location is sent only once

# Logging configuration
logging.basicConfig(level=logging.DEBUG)

# KivyMD ScreenManager
class LoginScreen(Screen):
    login = ObjectProperty(None)

class SignupScreen(Screen):
    signup = ObjectProperty(None)

class WelcomeScreen(Screen):
    welcome = ObjectProperty(None)
    user_name = StringProperty("")

class ForgotPasswordScreen(Screen):
    forget_pass = ObjectProperty(None)

class NotificationScreen(Screen):
    notifications = ObjectProperty(None)

class EmergencyContactScreen(Screen):
    pass

class FeedbackScreen(Screen):
    pass

class AboutusScreen(Screen):
    pass

class Edit_ProfileScreen(Screen):
    def on_pre_enter(self):
        # Load current user data into fields
        current_user = self.manager.get_screen('welcome').user_name
        try:
            with open(DATA_FILE, "r") as file:
                reader = csv.reader(file)
                for row in reader:
                    if row[0] == current_user:
                        self.ids.full_name.text = row[0]
                        self.ids.mobile.text = row[1]
                        self.ids.email.text = row[2]
                        break
        except Exception as e:
            logging.error(f"Error loading profile data: {e}")

# Function to save user data
def save_user_data(full_name, mobile, email, password):
    try:
        file_exists = os.path.isfile(DATA_FILE)
        with open(DATA_FILE, newline="", mode="a") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Name", "Mobile", "Email", "Password"])
            writer.writerow([full_name, mobile, email, password])
    except Exception as e:
        logging.error(f"Error saving user data: {e}")

# Function to check user credentials
def check_user_credentials(email, password):
    if not os.path.exists(DATA_FILE):
        return False, "Email not found"

    try:
        with open(DATA_FILE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                if not row:  # Skip empty rows
                    continue
                stored_name, stored_mobile, stored_email, stored_password = row
                if email.strip().lower() == stored_email.strip().lower():
                    if password.strip() == stored_password.strip():
                        return True, stored_name
                    else:
                        return False, "Incorrect password"
        return False, "Email not found"
    except Exception as e:
        logging.error(f"Error reading user data: {e}")
        return False, "Error reading user data"

# Function to generate OTP
def generate_otp():
    return str(random.randint(1000, 9999))

# Function to save OTP to a file
def save_otp_to_file(mobile_number, otp):
    try:
        with open(OTP_FILE, "w") as file:
            file.write(f"{mobile_number}:{otp}")
    except Exception as e:
        logging.error(f"Error saving OTP: {e}")

# Function to get saved OTP from a file
def get_saved_otp(mobile_number):
    try:
        if os.path.exists(OTP_FILE):
            with open(OTP_FILE, "r") as file:
                data = file.read()
                if f"{mobile_number}:" in data:
                    return data.split(f"{mobile_number}:")[1].split("\n")[0]
        return None
    except Exception as e:
        logging.error(f"Error reading OTP: {e}")
        return None

# Function to save new password
def save_new_password(mobile_number, new_password):
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                rows = list(csv.reader(file))

            for row in rows:
                if row[1] == mobile_number:
                    row[3] = new_password
                    break

            with open(DATA_FILE, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows(rows)
    except Exception as e:
        logging.error(f"Error saving new password: {e}")

# Function to save emergency contacts
def save_emergency_contacts(user_email, contacts):
    try:
        with open(f"{user_email}_emergency_contacts.txt", "w") as file:
            for contact in contacts:
                file.write(f"{contact}\n")
    except Exception as e:
        logging.error(f"Error saving emergency contacts: {e}")

# Function to load emergency contacts
def load_emergency_contacts(user_email):
    contacts = []
    try:
        with open(f"{user_email}_emergency_contacts.txt", "r") as file:
            for line in file:
                contacts.append(line.strip())
    except Exception as e:
        logging.error(f"Error loading emergency contacts: {e}")
    return contacts

# Custom toast function
def custom_toast(text, duration=1):
    label = Label(
        text=text,
        size_hint=(None, None),
        size=(300, 75),
        color=(0, 0, 0, 1),
        halign='center',
        valign='middle',
        font_size='18sp'
    )
    popup = Popup(
        content=label,
        size_hint=(None, None),
        size=(320, 70),
        background='assets/transparent.png'
    )
    popup.open()
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)

class MainScreen(Screen):
    pass

class ResultScreen(Screen):
    pass

# Main Application
class AccidentDetectionApp(MDApp):
    dialog = None
    otp_sent = ""
    emergency_contacts = []  # List to store emergency contacts
    location_sent = False  # To ensure location is sent only once

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_manager = MDFileManager(exit_manager=self.close_file_manager, select_path=self.select_file_path)
        self.file_path = ""
        self.monitor_thread = None

    def build(self):
        Builder.load_file('app.kv')
        Screen_manager = ScreenManager()
        Screen_manager.add_widget(LoginScreen(name='login'))
        Screen_manager.add_widget(SignupScreen(name='signup'))
        Screen_manager.add_widget(WelcomeScreen(name='welcome'))
        Screen_manager.add_widget(ForgotPasswordScreen(name='forgotpassword'))
        Screen_manager.add_widget(AboutusScreen(name='aboutus'))
        Screen_manager.add_widget(Edit_ProfileScreen(name='Edit_Profile'))
        Screen_manager.add_widget(NotificationScreen(name='notifications'))
        Screen_manager.add_widget(EmergencyContactScreen(name='emergency_contact'))
        Screen_manager.add_widget(FeedbackScreen(name='feedback'))
        Screen_manager.add_widget(MainScreen(name="main"))
        Screen_manager.add_widget(ResultScreen(name="results"))
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        return Screen_manager

    def make_emergency_call(self):
        """
        Make an emergency call using Twilio.
        """
        try:
            # Your Twilio account credentials
            account_sid = 'AC093d04199f3f6ca1ef6d52cc84ac1677'  # Replace with your Account SID
            auth_token = '85d5f2caaa3d8f82e38ebaf056f59fb9'     # Replace with your Auth Token

            # Create a Twilio client
            client = Client(account_sid, auth_token)

            # Generate TwiML with the custom message
            response = VoiceResponse()
            response.say("Accident detected. Please check Whatsapp message.", voice='alice', language='en-US')

            # Phone numbers
            to_number = '+919545792989'     # Recipient's number (replace)
            from_number = '+18562633414'    # Your Twilio number (replace)

            # Make the call with inline TwiML
            call = client.calls.create(
                twiml=str(response),  # Use generated TwiML
                to=to_number,
                from_=from_number
            )

            logging.debug(f"Emergency call initiated. Call SID: {call.sid}")
            self.show_toast("Emergency call initiated!")
        except Exception as e:
            logging.error(f"Failed to make emergency call: {e}")
            self.show_toast("Failed to make emergency call.")

    def send_emergency_alert(self, latitude, longitude):
        """
        Send emergency alerts to all contacts and initiate an emergency call.
        """
        if not self.location_sent:  # Ensure location is sent only once
            self.location_sent = True  # Set the flag to prevent multiple sends

            # Create the message with a Google Maps URL
            message = f"Emergency! Accident detected at https://maps.google.com/?q={latitude},{longitude}"
            logging.debug(f"Sending emergency alert: {message}")

            # Send the message to all emergency contacts
            for contact in self.emergency_contacts:
                try:
                    pywhatkit.sendwhatmsg_instantly(
                        contact,
                        message=message,
                        wait_time=30,
                        tab_close=True,
                        close_time=5
                    )
                    logging.debug(f"Alert sent to {contact}")
                except Exception as e:
                    logging.error(f"Failed to send alert to {contact}: {e}")

            self.show_toast("Emergency alerts sent!")

            # Make an emergency call after sending the location
            self.make_emergency_call()
        else:
            logging.debug("Location already sent. Skipping duplicate alert.")




    def show_toast(self, text):
        custom_toast(text, duration=3)

    def login(self, email, password):
        logging.debug(f"Attempting login with Email: {email} and Password: {password}")
        valid, message = check_user_credentials(email, password)
        if not email or not password:
            message = "Please fill in both fields."
            self.show_toast(message)
        elif valid:
            logging.debug(f"Login successful, transitioning to Welcome Screen with user {message}")
            self.root.get_screen("welcome").user_name = message
            self.root.current = "welcome"
            self.location_permission_popup()  # Show location permission popup
            # Load emergency contacts for the logged-in user
            self.emergency_contacts = load_emergency_contacts(email)
            self.update_emergency_contacts_list()
        else:
            logging.debug(f"Login failed: {message}")
            self.show_toast(message)

    def location_permission_popup(self):
        if not self.dialog:
            self.dialog = MDDialog(
                title="Location Access",
                text="Location access is required to proceed.",
                buttons=[MDFlatButton(
                        text="ALLOW", on_release=self.allow_location_permission
                    ),
                ],
            )
        self.dialog.open()

    def allow_location_permission(self, instance):
        self.dialog.dismiss()
        toast("Location access granted.")
        logging.debug("Location access granted")

    def toggle_password_visibility(self, password_field, eye_icon):
        password_field.password = not password_field.password  # Toggle password visibility
        eye_icon.icon = "eye-off" if password_field.password else "eye"  # Update eye icon

    def clear_content(self):
        screen = self.root.get_screen("login")
        screen.ids.password.text = ""
        screen.ids.email.text = ""

    def show_forgot_password_dialog(self):
        if not self.dialog:
            self.dialog = MDDialog(
                title="Forgot Password?",
                text="Please contact support for assistance.",
                buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())],
            )
        self.dialog.open()

    def register(self, full_name, mobile, email, password, otp):
        if not all([full_name, mobile, email, password, otp]):
            toast("Please fill all fields.", background=[1, 0, 0.1, 1])
            return

        if otp != self.otp_sent:
            toast("Incorrect OTP.", background=[1, 0, 0.1, 1])
            return
        save_user_data(full_name, mobile, email, password)
        toast("Registration Successful!", background=[0, 1, 0.1, 1])
        self.root.current = "welcome"

    def send_otp(self, mobile):
        if len(mobile) == 10:
            self.otp_sent = generate_otp()
            toast(f"OTP sent to {mobile}", background=[0, 1, 0, 1])
            message = f"""Your verification code is {self.otp_sent}"""
            Universal_mobo = "+91"+mobile
            pywhatkit.sendwhatmsg_instantly(Universal_mobo, message=message, wait_time=30, tab_close=True, close_time=5)
        else:
            toast("  Please enter a valid \n10-digit mobile number.", background=[1, 0, 0.1, 1])

    def update_password(self, mobile, new_password, confirm_password, otp):
        if not new_password or not confirm_password or not otp:
            toast("Please fill all fields.", background=[1, 0, 0.1, 1])
            return
        if new_password != confirm_password:
            toast("Passwords do not match.", background=[1, 0, 0.1, 1])
            return
        saved_otp = get_saved_otp(mobile)
        if saved_otp != otp:
            toast("Invalid OTP.", background=[1, 0, 0.1, 1])
            return
        save_new_password(mobile, new_password)

    def update_profile(self, full_name, mobile, email, current_pass, new_pass, confirm_pass):
        try:
            current_user = self.root.get_screen('welcome').user_name
            updated = False

            with open(DATA_FILE, "r") as file:
                rows = list(csv.reader(file))

            for row in rows:
                if row[0] == current_user:
                    if row[3] != current_pass:
                        toast("Current password incorrect", background=[1,0,0,1])
                        return

                    if new_pass != confirm_pass:
                        toast("New passwords don't match", background=[1,0,0,1])
                        return

                    row[0] = full_name
                    row[1] = mobile
                    row[2] = email
                    row[3] = new_pass
                    updated = True
                    break

            if updated:
                with open(DATA_FILE, "w", newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)
                toast("Profile updated successfully!", background=[0,1,0,1])
                self.root.current = 'welcome'
            else:
                toast("User not found!", background=[1,0,0,1])

        except Exception as e:
            logging.error(f"Error updating profile: {e}")
            toast("Update failed!", background=[1,0,0,1])

    def start_detection(self):
        """
        Start accident detection and simulate an accident.
        """
        logging.debug("Starting accident detection...")
        self.show_toast("Accident detection started!")
        self.root.current = "main"
        # Simulate accident detection after 5 seconds
        Clock.schedule_once(self.simulate_accident, 5)

    def simulate_accident(self, dt=None):
        """
        Simulate accident (accept optional 'dt' parameter for Clock).
        """
        logging.debug("Accident detected! Sending alerts...")
        self.show_toast("Accident detected! Sending alerts...")
        self.get_location()

    def get_location(self):
        """
        Fetch live GPS data or simulate GPS data based on the platform.
        """
        if not self.location_sent:  # Ensure location is sent only once
            if platform == 'android' or platform == 'ios':
                # Use plyer.gps for Android and iOS
                try:
                    gps.configure(on_location=self.on_location, on_status=self.on_status)
                    gps.start(minTime=1000, minDistance=1)  # Start GPS with minimum time and distance intervals
                    self.show_toast("Fetching live location...")
                except Exception as e:
                    logging.error(f"Error starting GPS: {e}")
                    self.show_toast("Failed to get location. Please enable GPS.")
            else:
                # Simulate GPS data for Windows or other platforms
                latitude = 18.4641  # Latitude for VIT Pune
                longitude = 73.8683  # Longitude for VIT Pune
                self.show_toast(f"Simulated Location: {latitude}, {longitude}")
                self.send_emergency_alert(latitude, longitude)

    def on_location(self, **kwargs):
        """
        Callback when live location is received.
        """
        latitude = kwargs.get("lat")
        longitude = kwargs.get("lon")
        if latitude and longitude:
            self.show_toast(f"Live Location: {latitude}, {longitude}")
            self.send_emergency_alert(latitude, longitude)
        else:
            self.show_toast("Failed to get live location.")

    def on_status(self, stype, status):
        """
        Callback for GPS status changes.
        """
        if stype == 'provider-enabled':
            self.show_toast("GPS enabled.")
        elif status == 'provider-disabled':
            self.show_toast("GPS disabled.")

    def add_emergency_contact(self, contact):
        """
        Add an emergency contact and update the RecycleView.
        """
        if contact and contact not in self.emergency_contacts:
            self.emergency_contacts.append(contact)
            self.update_emergency_contacts_list()
            # Save emergency contacts to file
            user_email = self.root.get_screen('welcome').user_name
            save_emergency_contacts(user_email, self.emergency_contacts)
        else:
            self.show_toast("Invalid or duplicate contact.")

    def remove_emergency_contact(self, contact):
        """
        Remove an emergency contact.
        """
        if contact in self.emergency_contacts:
            self.emergency_contacts.remove(contact)
            self.update_emergency_contacts_list()
            # Save emergency contacts to file
            user_email = self.root.get_screen('welcome').user_name
            save_emergency_contacts(user_email, self.emergency_contacts)
            self.show_toast(f"Removed {contact} from emergency contacts.")
        else:
            self.show_toast("Contact not found.")

    def update_emergency_contacts_list(self):
        """
        Update the RecycleView with the current emergency contacts.
        """
        contacts_list = self.root.get_screen('emergency_contact').ids.contacts_list
        contacts_list.data = []
        for contact in self.emergency_contacts:
            contacts_list.data.append({
                "text": contact,
                "theme_text_color": "Custom",  # Use custom text color
                "text_color": [0, 0, 0, 1]  # Black text color (RGBA)
            })

    def toggle_notifications(self, active):
        """
        Toggle notifications on or off.
        :param active: Boolean, True if notifications are enabled, False otherwise.
        """
        self.notifications_enabled = active
        if active:
            self.show_toast("Notifications enabled")
        else:
            self.show_toast("Notifications disabled")

    def open_file_manager(self):
        self.file_manager.show(os.getcwd())  # Show current working directory

    def close_file_manager(self, *args):
        self.file_manager.close()

    def select_file_path(self, path):
        self.root.get_screen("main").ids.file_path.text = path
        self.file_manager.close()

    def start_monitoring(self):
        file_path = self.root.get_screen("main").ids.file_path.text
        if not os.path.exists(file_path):
            self.show_dialog("Error", "Invalid file path! Please select a valid file.")
            return

        self.file_path = file_path
        self.root.current = "results"  # Ensure the correct screen name is used
        self.monitor_thread = threading.Thread(target=self.monitor_sensor_data, daemon=True)
        self.monitor_thread.start()

    def monitor_sensor_data(self):
        """
        Automatically monitors the sensor data file at regular intervals.
        """
        while True:
            file_path = self.file_path
            if os.path.exists(file_path):
                gyroscope_data, accelerometer_data = self.read_sensor_data_from_file(file_path)
                accident_detected = self.detect_accident(gyroscope_data, accelerometer_data)
                if accident_detected:
                    # Show accident results in the UI
                    Clock.schedule_once(lambda *args: self.show_accident_results(["Accident detected!"]))
                    # Send location and make emergency call
                    self.get_location()
                    break  # Stop monitoring after sending the location
            time.sleep(15)  # Check every 15 seconds

    def read_sensor_data_from_file(self, file_path):
        gyroscope_data = []
        accelerometer_data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                next(file)  # Skip header
                for line in file:
                    parts = line.strip().split(',')
                    if len(parts) == 7:
                        print(parts[1:4])
                        gx, gy, gz = map(float, parts[1:4])
                        ax, ay, az = map(float, parts[4:7])
                        gyroscope_data.append((gx, gy, gz))
                        accelerometer_data.append((ax, ay, az))
        except Exception as e:
            self.show_dialog("File Error", f"Could not read {file_path}. Ensure the format is correct.")
            logging.error(f"Error reading file {file_path}: {e}")  # Log error
        return gyroscope_data, accelerometer_data

    def detect_accident(self, gyroscope_data, accelerometer_data):
        """
        Detect if an accident has occurred based on sensor data.
        """
        ax_data = [ax for ax, ay, az in accelerometer_data]
        smoothed_ax = self.moving_average(ax_data, 5)

        for i, (gx, gy, gz) in enumerate(gyroscope_data):
            if abs(gx) > GYRO_THRESHOLD or abs(gy) > GYRO_THRESHOLD or abs(gz) > GYRO_THRESHOLD:
                return True  # Accident detected
            if i < len(smoothed_ax) and abs(smoothed_ax[i]) > ACCEL_THRESHOLD:
                return True  # Accident detected
        return False  # No accident detected
    def moving_average(self, data, window_size):
        if len(data) < window_size:
            return data
        return [sum(data[i:i + window_size]) / window_size for i in range(len(data) - window_size + 1)]

    def show_accident_results(self, results):
        def update_ui(*args):
            # Clear previous results
            results_list = self.root.get_screen("results").ids.results_list
            results_list.clear_widgets()

            # Add new results inside MDCard for better UI
            for result in results:
                card = MDCard(
                    size_hint=(None, None),
                    size=("280dp", "100dp"),
                    padding=("10dp"),
                    elevation=10,
                    radius=[10, 10, 10, 10],
                    orientation="vertical"
                )
                card.add_widget(MDLabel(text=result, theme_text_color="Secondary", halign="left", size_hint_y=None, height="40dp"))
                results_list.add_widget(card)

        # Schedule UI update on the main thread
        Clock.schedule_once(update_ui)

        # Show the dialog asking if the person is okay only if the dialog hasn't been shown yet
        if not accident_prompt_shown:
            self.prompt_user_for_response()

    def prompt_user_for_response(self):
        global accident_prompt_shown
        if not accident_prompt_shown:
            self.dialog = MDDialog(  # Use self.dialog to reference the dialog
                title="Accident Detected",
                text="Are you okay?",
                buttons=[
                    MDFlatButton(text="YES", on_release=self.user_is_okay),
                    MDRaisedButton(text="NO", on_release=self.user_not_okay),  # Call user_not_okay
                ],
            )
            self.dialog.open()
            self.scheduled_call = Clock.schedule_once(self.user_not_okay, 7)  # Schedule user_not_okay

    def user_is_okay(self, *args):
        Clock.unschedule(self.scheduled_call)
        self.show_dialog("Response", "Glad to hear you're okay!")
        global accident_prompt_shown
        accident_prompt_shown = True  # Prevent the dialog from appearing again
        if self.dialog:
            self.dialog.dismiss()  # Dismiss the dialog
        self.show_dialog("Response", "Glad to hear you're okay!")

    def user_not_okay(self, *args):
        """
        Handle "NO" button click.
        """
        self.start_monitoring()
        self.simulate_accident()
        global accident_prompt_shown
        accident_prompt_shown = True
        if self.dialog:
            self.dialog.dismiss()

    def show_dialog(self, title, message):
        Clock.schedule_once(lambda dt: self._show_dialog(title, message), 0)

    def _show_dialog(self, title, message):
        self.dialog = MDDialog(
            title=title,
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def go_back_to_main(self):
        global accident_loop_exit
        accident_loop_exit = True
        self.root.current = "welcome"

# Run the application
if __name__ == "__main__":
    AccidentDetectionApp().run()