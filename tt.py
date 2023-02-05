import datetime

if __name__ == '__main__':

    start_date = datetime.datetime.now() - datetime.timedelta(weeks=52)
    print("{}".format( str(start_date)[:10]))
