
import config
import database

# Open and initialise your existing database
database.init_db()

# Connect to the database
connection = database.get_connection()

# Update the sample exchange rates
for code, rate in config.SAMPLE_RATES_TO_USD.items():

    connection.execute(
        """
        UPDATE exchange_rate
        SET rate_to_usd = ?
        WHERE currency_code = ? AND source = 'sample'
        """,
        (float(rate), code)
    )

# Save the changes
connection.commit()

# Close the database
connection.close()

print("Sample exchange rates updated successfully!")
