import time


def run_to_fail():

    print("This script will fail.")
    print("Countdown to failure starting.")
    for i in range(10, 0, -1):
        print("Failing in {s} seconds".format(s=i))
        time.sleep(1)

    raise Exception("I failed!")


if __name__ == "__main__":
    run_to_fail()
