import random as rd

def count_cycles(order):
    """
    Return the list of lengths of each cycle in the permutation.
    """
    visited = [False] * len(order)  # Track visited prisoners
    cycles = []  # List to store the lengths of cycles

    for i in range(len(order)):
        if not visited[i]:  # If the prisoner has not been visited
            cycle_length = 0
            current = i

            while not visited[current]:  # Traverse the cycle
                visited[current] = True  # Mark prisoner as visited
                current = order[current] - 1  # Move to the next prisoner in the cycle
                cycle_length += 1  # Increment cycle length

            cycles.append(cycle_length)  # Add cycle length to the list

    return cycles

def do_monte_carlo_simulation(num_trials):
    """
    Perform Monte Carlo simulation to find chance that one cycle is longer than 50.
    """
    count = 0  # Counter for successful trials

    for _ in range(num_trials):
        if _ % 10000 == 0:  # Print percentage progress every 10,000 trials
            print(f"{_ / num_trials:.2%} completed")
        order = [i for i in range(1, 101)]  # List of prisoners
        rd.shuffle(order)  # Shuffle the list to randomize the order of prisoners
        cycles = count_cycles(order)  # Get the lengths of cycles

        if any(cycle > 50 for cycle in cycles):  # Check if any cycle is longer than 50
            count += 1  # Increment counter if condition is met

    return count / num_trials  # Return the probability

order = [i for i in range(1, 101)]  # List of prisoners
rd.shuffle(order)  # Shuffle the list to randomize the order of prisoners
print(count_cycles(order))  # Print the lengths of cycles in the permutation
result = do_monte_carlo_simulation(1000000)
print(f"Chance that one cycle is longer than 50: {result:.2%}")  # Print the probability
