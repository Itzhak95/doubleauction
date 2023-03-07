# This program implements Gjerstad and Dickhaut's (1998) model of the double auction
# To simplify the code, we assume infinite memory
# I also endow each seller with one unit; and give each buyer unit demand

import numpy as np
from scipy.interpolate import CubicSpline
from random import choices

# PARAMETERS

# Set the buyer valuations and seller costs

input_values = [100, 200, 300, 400, 500]

input_costs = [195, 245, 295, 345, 395]

# Set the value of the 'very high' ask (resp., bid) which will never (resp., always) be accepted

m = 1000

# Set the maximum length l of every round

l = 150

# Set the number of rounds

r = 2

# Set the number of transactions that are remembered

memory = 3

# Set the replacement rule (0 = no replacement, 1 = perfect replacement, 2 = random replacement)

replacement = 0

# HISTORIES

# As a preliminary, calculate the number of buyers/sellers

n = len(input_values)

# We now define some lists which keep track of historic market activity across all rounds
# Note that data associated with a different transactions are separated into different sub-lists

bids = [[]]

asks = [[]]

accepted_bids = [[]]

rejected_bids = [[]]

accepted_asks = [[]]

rejected_asks = [[]]

# Do we need this?
union = []

# SELLER BELIEFS

# As a preliminary, define a function which extracts the remembered elements from a list

def mem(a_list):
    flattened_list = []
    if len(a_list) < memory:
        for sub_list in a_list:
            for item in sub_list:
                flattened_list.append(item)
    else:
        for sub_list in a_list[-memory:]:
            for item in sub_list:
                flattened_list.append(item)
    return flattened_list


# Count the number of taken (i.e. accepted) asks that are greater than or equal to a

def tag(a):
    return len([ask for ask in mem(accepted_asks) if ask >= a])

# Count the number of bids that are greater than or equal to a

def bg(a):
    return len([bid for bid in mem(bids) if bid >= a])

# Count the total number of rejected asks that are less than or equal to a

def ral(a):
    return len([ask for ask in mem(rejected_asks) if ask <= a])

# Define the seller beliefs (defined ONLY over the set of bids and asks in the history, plus 0 and m).

def p_hat(a):
    if a == 0:
        return 1.0
    elif a >= m:
        return 0.0
    else:
        return (tag(a) + bg(a)) / (tag(a) + bg(a) + ral(a))

# Now extend these beliefs over the reals, while also taking care of asks outside of the bid/ask spread

def p(a):
    # Asks that are below the market bid (this always includes 0) must be accepted
    if a <= market_bid:
        return 1.0
    # Asks that are above the market ask (this always includes m) are never accepted
    elif a >= market_ask:
        return 0.0
    # Asks in the union of historic bids and asks have already been defined
    elif a in union:
        return p_hat(a)
    # Otherwise, we use cubic interpolation
    else:
        # Find the largest bid/ask that is lower than a
        lower = 0
        try:
            lower = max(element for element in union if element < a)
        except:
            pass
        # Find the smallest bid/ask that is higher than a
        higher = m
        try:
            higher = min(element for element in union if element > a)
        except:
            pass
        # Interpolate between the two
        x = np.array([lower, higher])
        y = np.array([p_hat(lower), p_hat(higher)])
        cs = CubicSpline(x, y, bc_type='clamped')
        return cs(a)

# BUYER BELIEFS

# Count the taken (i.e. accepted) bids that are less than or equal to b

def tbl(b):
    return len([bid for bid in mem(accepted_bids) if bid <= b])

# Count the asks that are less than or equal to b

def al(b):
    return len([ask for ask in mem(asks) if ask <= b])

# Count the rejected bids that are greater than or equal to b

def rbg(b):
    return len([bid for bid in mem(rejected_bids) if bid >= b])

# Define the buyer beliefs (defined ONLY over the set of bids and asks in the history, plus 0 and m).

def q_hat(b):
    if b == 0:
        return 0.0
    elif b >= m:
        return 1.0
    else:
        return (tbl(b) + al(b))/(tbl(b) + al(b) + rbg(b))

# Extend these beliefs over the reals as before, again taking account of the spread reduction rule

def q(b):
    # Bids below the market bid cannot be accepted
    if b <= market_bid:
        return 0.0
    # Bids above the market ask must be accepted
    elif b >= market_ask:
        return 1.0
    # Bids in the list of historic bids and asks have already been defined
    elif b in union:
        return q_hat(b)
    # Otherwise, we use cubic interpolation
    else:
        lower = 0
        try:
            lower = max(element for element in union if element < b)
        except:
            pass
        higher = m
        try:
            higher = min(element for element in union if element > b)
        except:
            pass
        x = np.array([lower, higher])
        y = np.array([q_hat(lower), q_hat(higher)])
        cs = CubicSpline(x, y, bc_type='clamped')
        return cs(b)

# OPTIMISATION

# Define the seller's payoff given that they have cost c and ask for a

def s_payoff(c, a):
    return (a - c)*p(a)

# Calculate the seller's optimal ask given that they have cost c (I do the optimisation using brute force)
# Observe that this function returns the optimal ask as the first entry, and the associated payoff as the second

def optimal_ask(c):
    # If the seller were called on to play, then the last ask must have been rejected
    if market_ask != m:
        rejected_asks[t].append(market_ask)
    # Now calculate the expected payoff from every possible ask
    payoffs = [s_payoff(c, a) for a in spread]
    max_payoff = max(payoffs)
    # The seller hasn't actually been called to play yet, so undo the 'damage'
    if market_ask != m:
        rejected_asks[t].remove(market_ask)
    # Return the results
    if max_payoff > 0:
        return [payoffs.index(max_payoff) + min(spread), max_payoff]
    else:
        return [m, 0.0]

# Analogously, define the buyer's payoff given that they have value v and ask for b

def b_payoff(v, b):
    return (v - b)*q(b)

# Calculate a buyer's optimal bid given that they have value v
# As before, this function also returns the payoff generated by the optimal bid

def optimal_bid(v):
    # If the buyer were called to play, then the last bid was rejected
    if market_bid != 0:
        rejected_bids[t].append(market_bid)
    # Now find the optimal bid
    payoffs = [b_payoff(v, b) for b in spread]
    max_payoff = max(payoffs)
    # The buyer hasn't actually been called to play yet, so 'undo' the damage
    if market_bid != 0:
        rejected_bids[t].remove(market_bid)
    # Return the results
    if max_payoff > 0:
        return [payoffs.index(max_payoff) + min(spread), max_payoff]
    else:
        return [0, 0.0]

# TIMING

# The chance that a trader is chosen to move is proportional to their expected payoff from moving

# This function calculates the chance that each player will move

def p_move():
    buyer_payoffs = [optimal_bid(v)[1] for v in values]
    seller_payoffs = [optimal_ask(c)[1] for c in costs]
    all_payoffs = buyer_payoffs + seller_payoffs
    normalisation = sum(all_payoffs)
    if normalisation > 0:
        return [i/normalisation for i in all_payoffs]

# This function chooses a player to move

def choose_player():
    probabilities = p_move()
    if probabilities is not None:
        players = buyers + sellers
        weights = probabilities
        return choices(players, weights)[0]

# SIMULATIONS

# Define some lists that will be used to collect the results

all_prices = []
number_of_trades = []
all_buyer_values = []
all_seller_costs = []

# Define a variable that counts the number of transactions

t = 0

# Now start the simulation

for element in range(r):
    # At the start of a round, refresh the buyer/seller valuations
    buyers = list(range(0, n))
    sellers = list(range(n, 2*n))
    values = [element for element in input_values]
    costs = [element for element in input_costs]
    # Reset the spread
    market_bid = 0
    market_ask = m
    spread = list(range(market_bid, market_ask + 1))
    active_bidder = 100
    active_seller = 100
    # Reset the lists used for data collection
    prices = []
    buyer_values = []
    seller_costs = []
    trades = 0
    # The round now begins
    iteration = 0
    for time in range(l):
        iteration += 1
        print(f'Move: {iteration}')
        # First, choose a player
        player = choose_player()
        if player is None:
            print("End of round")
            break
        print(f'Player: {player}')
        # Suppose first they are a buyer
        if player in buyers:
            print('[Buyer]')
            # The last bid must have been rejected
            if market_bid != 0:
                rejected_bids[t].append(market_bid)
            print(f'Rejected bids: {rejected_bids}')
            index = buyers.index(player)
            valuation = values[index]
            print(f'Valuation {valuation}')
            bid = optimal_bid(valuation)[0]
            # They might choose to accept the market ask, leading to transaction
            if bid == market_ask:
                trades += 1
                print(f'Trades {trades}')
                prices.append(bid)
                print(f'Trades {prices}')
                buyer_values.append(valuation)
                accepted_asks[t].append(bid)
                print(f'Accepted asks {accepted_asks}')
                # Following the transaction, we need to reset the bid/ask spread
                market_bid = 0
                print(f'Market bid {market_bid}')
                market_ask = m
                print(f'Market ask {market_ask}')
                # We also remove the buyer/seller (and their value/cost) from the market
                if replacement != 1:
                    buyers.remove(player)
                    values.remove(valuation)
                print(f'Buyers {buyers}')
                print(f'Values {values}')
                print(f'Active seller {active_seller}')
                index = sellers.index(active_seller)
                cost = costs[index]
                seller_costs.append(cost)
                if replacement != 1:
                    costs.remove(cost)
                    sellers.remove(active_seller)
                print(f'Costs {costs}')
                print(f'Sellers {sellers}')
                # Finally, increment the transactions counter
                t += 1
                for x in [bids, asks, accepted_bids, rejected_bids, accepted_asks, rejected_asks]:
                    x.append([])
            # Alternatively, they might just be making a (positive) bid
            elif market_ask > bid > 0:
                active_bidder = player
                print(f'Active bidder {active_bidder}')
                bids[t].append(bid)
                print(f'Bids {bids}')
                if market_ask != m:
                    rejected_asks[t].append(market_ask)
                print(f'Rejected asks {rejected_asks}')
                market_bid = bid
                print(f'Market bid: {market_bid}')
        # Instead, the player might be a seller
        elif player in sellers:
            print('[Seller]')
            # The last ask was rejected
            if market_ask != m:
                rejected_asks[t].append(market_ask)
            print(f'Rejected asks: {rejected_asks}')
            index = sellers.index(player)
            valuation = costs[index]
            print(f'Cost: {valuation}')
            ask = optimal_ask(valuation)[0]
            print(f'Ask: {ask}')
            # They might choose to accept the market bid, leading to a transaction
            if ask == market_bid:
                trades += 1
                print(f'Trades {trades}')
                prices.append(ask)
                print(f' Prices {prices}')
                accepted_bids[t].append(ask)
                print(f' Accepted bids {accepted_bids}')
                seller_costs.append(valuation)
                # Following the transaction, we need to reset the bid/ask spread
                market_bid = 0
                print(f' Market bid {market_bid}')
                market_ask = m
                print(f' Market ask {market_ask}')
                # We also remove the seller/buyer (and their cost/value) from the market
                if replacement != 1:
                    sellers.remove(player)
                    costs.remove(valuation)
                print(f' Sellers {sellers}')
                print(f' Costs {costs}')
                index = buyers.index(active_bidder)
                valuation = values[index]
                buyer_values.append(valuation)
                if replacement != 1:
                    values.remove(valuation)
                    buyers.remove(active_bidder)
                print(f' Values {values}')
                print(f' Buyers {buyers}')
                # Finally, increment the transactions counter
                t += 1
                for x in [bids, asks, accepted_bids, rejected_bids, accepted_asks, rejected_asks]:
                    x.append([])
            # They might instead be just making an ask (less than m)
            elif market_bid < ask < m:
                active_seller = player
                print(f'Active seller {active_seller}')
                asks[t].append(ask)
                print(f'Asks: {asks}')
                if market_bid != 0:
                    rejected_bids[t].append(market_bid)
                print(f'Rejected bids: {rejected_bids}')
                market_ask = ask
                print(f'Market ask: {market_ask}')
        # In either case, we should update the spread and union lists:
        spread = list(range(market_bid, market_ask+1))
        union = list(dict.fromkeys(mem(asks) + mem(bids) + [0, m]))
        print(f'union: {union}')
        print('------')
    # Save the data from this round
    all_prices.append(prices)
    number_of_trades.append(trades)
    all_buyer_values.append(buyer_values)
    all_seller_costs.append(seller_costs)

# Finally, print the results
print('RESULTS')
print(f'Prices: {all_prices}')
print(f'Trades: {number_of_trades}')
print(f'Buyer values: {all_buyer_values}')
print(f'Seller costs: {all_seller_costs}')
