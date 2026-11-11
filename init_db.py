import config
import database

def main(db_file=config.DB_FILE):
    database.init_db(db_file)
    print("Database created:",db_file)

if __name__ == "__main__":
    main()