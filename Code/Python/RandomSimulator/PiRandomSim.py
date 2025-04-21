def pi_random_sim(n):
    """
    Calculate PI by random n points and check the chance that the points are in the circle.
    """
    import random as rd
    count = 0
    for i in range(n):
        x = rd.random()
        y = rd.random()
        if x**2 + y**2 <= 1:
            count += 1
    return 4 * count / n

if __name__ == '__main__':
    import math
    result = pi_random_sim(100000000)
    print("Accuracy (%): ", result / math.pi * 100)