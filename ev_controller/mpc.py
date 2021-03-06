import matplotlib.pyplot as plt
import numpy as np
import time
import cvxpy
from scipy.interpolate import interp1d

NUM_CARS = 4
CONTROL_HORIZON = 24*6
SIMULATION_TIME = 24*6


def get_parameters():
    alpha = 1
    beta = 0.001
    gamma = 1
    u_max = 0.1
    u_tot_max = 0.03
    return alpha, beta, gamma, u_max, u_tot_max

def get_data():

    #TODO(Mathilde): find prices from caiso
    prices_day = np.array([1, 1, 1, 1, 8, 9, 8, 8, 6, 5, 4, 4, 5, 5, 6, 6, 7, 10, 12, 7, 5, 3, 2, 1])
    time_set = np.linspace(0, 23, SIMULATION_TIME)
    prices = interp1d(range(len(prices_day)), prices_day)
    prices = prices(time_set)
    for i in range(int(SIMULATION_TIME/len(prices_day))-1):
        prices = np.concatenate((prices, prices_day))
    prices = np.concatenate((prices, [0]))

    cars_presence = np.ones((NUM_CARS, SIMULATION_TIME))
    for j in range(SIMULATION_TIME-50):
        cars_presence[1, j] = 0

    return prices, cars_presence

def simulation(x, u):
    A, B = get_real_matrix()
    return np.dot(A, x) + np.dot(B, u)

def mpc_control(x0):
    x = cvxpy.Variable(NUM_CARS, CONTROL_HORIZON+1)
    u = cvxpy.Variable(NUM_CARS, CONTROL_HORIZON)

    A, B = get_model_matrix()
    Q, R = get_cost_matrix()

    alpha, beta, gamma, u_max, u_tot_max = get_parameters()

    prices = get_data()[0]

    cost = 0
    constraints = []

    for t in range(CONTROL_HORIZON):
        #cost += sum(u[:, t]*prices[t]) + sum(1 - x[:, t]) * beta
        cost += cvxpy.quad_form((np.ones((NUM_CARS)) - x[:, t+1]), Q[:, :, t])
        cost += cvxpy.quad_form(u[:, t], R[:, :, t])
        constraints += [x[:, t+1] == A[:, :, t] * x[:, t] + B[:, :, t] * u[:, t]]
        constraints += [u[:, t] >= 0, u[:, t] <= np.ones((NUM_CARS)) - x[:, t]]
        constraints += [u[:, t] <= u_max]
        constraints += [np.sum(u[:, t]) <= u_tot_max]
    constraints += [x[:, 0] == x0]

    prob = cvxpy.Problem(cvxpy.Minimize(cost), constraints)

    start = time.time()
    prob.solve(verbose=False)
    elapsed_time = time.time() - start
    print('calculation time: {0} [sec]'.format(elapsed_time))

    if prob.status == cvxpy.OPTIMAL:
        return x.value

def get_model_matrix():
    gamma = get_parameters()[2]
    cars_presence = get_data()[1]

    A = np.zeros((NUM_CARS, NUM_CARS, SIMULATION_TIME))
    B = np.zeros((NUM_CARS, NUM_CARS, SIMULATION_TIME))

    for i in range(SIMULATION_TIME):
        A[:, :, i] = np.eye(NUM_CARS)
        B[:, :, i] = np.eye(NUM_CARS) * gamma

    for i in range(NUM_CARS):
        A[i, i, :] = np.multiply(A[i, i, :], cars_presence[i, :])
        B[i, i, :] = np.multiply(B[i, i, :], cars_presence[i, :])

    return A, B

def get_cost_matrix():
    prices, cars_presence = get_data()
    beta = get_parameters()[1]

    Q = np.zeros((NUM_CARS, NUM_CARS, SIMULATION_TIME))
    R = np.zeros((NUM_CARS, NUM_CARS, SIMULATION_TIME))

    for i in range(SIMULATION_TIME):
        R[:, :, i] = np.eye(NUM_CARS) * prices[i+1]**2
        Q[:, :, i] = np.eye(NUM_CARS) * beta

    for i in range(NUM_CARS):
        R[i, i, :] = np.multiply(R[i, i, :], cars_presence[i, :])
        Q[i, i, :] = np.multiply(Q[i, i, :], cars_presence[i, :])

    return Q, R


if __name__ == '__main__':
    x = mpc_control(np.array([0, 0, 0, 0]))
    print(x)
    prices, cars_presence  = get_data()
    plt.figure(figsize=(10, 7))
    for i in range(NUM_CARS):
        plt.plot(range(CONTROL_HORIZON+1), x[i, :].T, label='soc of car '+str(i))
    plt.plot(range(CONTROL_HORIZON), prices[:CONTROL_HORIZON]/max(prices), label='prices')
    plt.title('charging schedule for 24h')
    plt.xlabel('time')
    plt.ylabel('energy')
    plt.legend()
    plt.grid()
    plt.savefig('result_mpc.png')



