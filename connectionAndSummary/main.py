# Import necessary modules
import os
import mysql.connector
import pandas as pd
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def configure_api_and_db():
    """Configure API key for Google Generative AI and set up MySQL connection."""
    try:
        API_KEY = "api-key"
        if not API_KEY:
            raise ValueError("API Key not found in environment variables.")
        
        genai.configure(api_key=API_KEY)

        # Establishing MySQL database connection
        db_connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="web_scraping"
        )
        print("Database connected successfully.")
        return db_connection
    except Exception as e:
        print(f"Error during configuration: {e}")
        return None

def summarize_text(text):
    """Generate a summarized version of the given text using Google Generative AI."""
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        response = model.generate_content([{"prompt": f"Summarize this text: {text}"}])
        return response.text if response else "N/A"
    except Exception as e:
        print(f"Error during text summarization: {e}")
        return text  # Fallback to original text if summarization fails

def scrape_category_data(categories, base_url):
    """Scrape category name, links, and descriptions from the provided categories."""
    scraped_data = {'Category_Name': [], 'links': [], 'Description': []}

    for html in categories:
        # Extract category name
        heading_tag = html.find('h3')
        heading = heading_tag.text.strip() if heading_tag else "N/A"

        # Extract link
        link_tag = html.find('a', href=True)
        link = base_url + link_tag['href'] if link_tag else "N/A"

        # Extract description
        description_tag = html.find('div', {'itemprop': 'description'})
        description = description_tag.text.strip() if description_tag else "N/A"

        # Append to dictionary
        scraped_data['Category_Name'].append(heading)
        scraped_data['links'].append(link)
        scraped_data['Description'].append(description)

    return scraped_data

def insert_into_db(db_connection, data):
    """Insert scraped data into MySQL database."""
    try:
        cursor = db_connection.cursor()
        # Check if the table exists, create if not
        cursor.execute("SHOW TABLES LIKE 'scraped_data'")
        if cursor.fetchone() is None:
            cursor.execute("""
                CREATE TABLE scraped_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    category_name VARCHAR(255),
                    link TEXT,
                    description TEXT
                );
            """)

        # Insert data
        sql_query = """
        INSERT INTO scraped_data (category_name, link, description)
        VALUES (%s, %s, %s)
        """
        for i in range(len(data['Category_Name'])):
            cursor.execute(sql_query, (data['Category_Name'][i], data['links'][i], data['Description'][i]))

        db_connection.commit()
        print("Data inserted successfully into the MySQL database!")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")

    finally:
        if db_connection.is_connected():
            cursor.close()
            db_connection.close()
            print("MySQL connection is closed.")

def main():
    """Main function to orchestrate the scraping and database insertion."""
    db_connection = configure_api_and_db()
    if not db_connection:
        return

    try:
        base_url = "https://gov.optimism.io"
        response = requests.get(base_url)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch data from {base_url}, status code: {response.status_code}")

        soup = BeautifulSoup(response.content, "html.parser")
        categories = soup.find_all("td", class_="category")
        
        if not categories:
            raise ValueError("No categories found in the HTML page.")

        # Scrape data
        scraped_data = scrape_category_data(categories, base_url)

        # Insert data into the database
        insert_into_db(db_connection, scraped_data)

    except Exception as e:
        print(f"Error in main execution: {e}")

if __name__ == "__main__":
    main()
