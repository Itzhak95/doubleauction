# This program implements Gjerstad and Dickhaut's (1998) model of the double auction

# To simplify the code, we assume infinite memory
# I also endow each seller with one unit; and give each buyer unit demand

# To do: CHECK A FULL SIMULATION!

import numpy as np
from scipy.interpolate import CubicSpline
from random import choices

# PARAMETERS

# Define the set of buyers and their valuations

buyers = list(range(0, 4))

values = [225, 260, 280, 305]

# Define the set of sellers and their costs

sellers = list(range(4, 8))

costs = [140, 165, 190, 230]

# Set the value of the 'very high' ask (resp, bid) which will never (resp, always) be accepted

m = 1000

# Set the length l of every round

l = 40

# Set the number of rounds

r = 5

# HISTORIES

# We now define some lists which keep track of historic market activity

bids = [0]

asks = [m]

accepted_bids = []

rejected_bids = []

accepted_asks = []

rejected_asks = []

union = asks + bids

prices = []

trades = 0

market_bid = 0

market_ask = m

active_bidder = 100

active_seller = 100

spread = list(range(market_bid, market_ask+1))

# SELLER BELIEFS

# Count the number of taken (i.e. accepted) asks that are greater than or equal to a

def tag(a):
    return len([ask for ask in accepted_asks if ask >= a])

# Count the number of bids that are greater than or equal to a

def bg(a):
    return len([bid for bid in bids if bid >= a])

# Count the total number of rejected asks that are less than or equal to a

def ral(a):
    return len([ask for ask in rejected_asks if ask <= a])

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
    return len([bid for bid in accepted_bids if bid <= b])

# Count the bids that are less than or equal to b

def al(b):
    return len([ask for ask in asks if ask <= b])

# Count the rejected bids that are greater than or equal to b

def rbg(b):
    return len([bid for bid in rejected_bids if bid >= b])

# Define the buyer beliefs (defined ONLY over the set of bids and asks in the history, plus 0 and m).

def q_hat(b):
    if b == 0:
        return 0.0
    elif b >= m:
        return 1.0
    else:
        return (tbl(b) + al(b))/(tbl(b) + al(b) + rbg(b))

# Extend these beliefs over the reals as before

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
    # If the seller were called to play, then the last ask was rejected
    rejected_asks.append(market_ask)
    # Now find the optimal ask
    payoffs = [s_payoff(c, a) for a in spread]
    # The seller hasn't actually been called to play yet, so undo the damage
    rejected_asks.remove(market_ask)
    # Return the results
    if max(payoffs) > 0:
        return [payoffs.index(max(payoffs)) + min(spread), max(payoffs)]
    else:
        return [m, 0.0]

# Analogously, define the buyer's payoff given that they have value v and ask for b

def b_payoff(v, b):
    return (v - b)*q(b)

# Calculate a buyer's optimal bid given that they have value v
# As before, this function also returns the payoff generated by the optimal bid

def optimal_bid(v):
    # If the buyer were called to play, then the last bid was rejected
    rejected_bids.append(market_bid)
    # Now find the optimal bid
    payoffs = [b_payoff(v, b) for b in spread]
    # The buyer hasn't actually been called to play yet, so 'undo' the damage
    rejected_bids.remove(market_bid)
    # Return the results
    if max(payoffs) > 0:
        return [payoffs.index(max(payoffs)) + min(spread), max(payoffs)]
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
    return [i/normalisation for i in all_payoffs]

# This function chooses a player to move

def choose_player():
    players = buyers + sellers
    weights = p_move()
    return choices(players, weights)[0]

# SIMULATIONS

for time in range(l):
    # First, choose a player
    player = choose_player()
    print(f'Player: {player}')
    # Suppose first they are a buyer
    if player in buyers:
        # The last bid was rejected
        rejected_bids.append(market_bid)
        print(f'Rejected bids: {rejected_bids}')
        print('[Buyer]')
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
            accepted_asks.append(bid)
            print(f'Accepted asks {accepted_asks}')
            # Following the transaction, we need to reset the bid/ask spread
            market_bid = 0
            print(f'Market bid {market_bid}')
            market_ask = m
            print(f'Market ask {market_ask}')
            # We also remove the buyer/seller (and their value/cost) from the market
            buyers.remove(player)
            print(f'Buyers {buyers}')
            values.remove(valuation)
            print(f'Values {values}')
            print(f'Active seller {active_seller}')
            index = sellers.index(active_seller)
            cost = costs[index]
            costs.remove(cost)
            print(f'Costs {costs}')
            sellers.remove(active_seller)
        # Alternatively, they might just be making a (positive) bid
        elif market_ask > bid > 0:
            active_bidder = player
            print(f'Active bidder {active_bidder}')
            bids.append(bid)
            print(f'Bids {bids}')
            rejected_asks.append(market_ask)
            print(f'Rejected asks {rejected_asks}')
            market_bid = bid
            print(f'Market bid: {market_bid}')
    # Instead, the player might be a seller
    elif player in sellers:
        # The last ask was rejected
        rejected_asks.append(market_ask)
        print(f'Rejected asks: {rejected_asks}')
        print('[Seller]')
        index = sellers.index(player)
        valuation = costs[index]
        print(f'Valuation: {valuation}')
        ask = optimal_ask(valuation)[0]
        print(f'Ask: {ask}')
        # They might choose to accept the market bid, leading to a transaction
        if ask == market_bid:
            trades += 1
            print(f'Trades {trades}')
            prices.append(ask)
            print(f' Prices {prices}')
            accepted_bids.append(ask)
            print(f' Accepted bids {accepted_bids}')
            # Following the transaction, we need to reset the bid/ask spread
            market_bid = 0
            print(f' Market bid {market_bid}')
            market_ask = m
            print(f' Market ask {market_ask}')
            # We also remove the seller/buyer (and their cost/value) from the market
            sellers.remove(player)
            print(f' Sellers {sellers}')
            costs.remove(valuation)
            print(f' Costs {costs}')
            index = buyers.index(active_bidder)
            valuation = values[index]
            values.remove(valuation)
            print(f' Values {values}')
            buyers.remove(active_bidder)
            print(f' Buyers {buyers}')
        # They might instead be just making an ask (less than m)
        elif market_bid < ask < m:
            active_seller = player
            print(f'Active seller {active_seller}')
            asks.append(ask)
            print(f'Asks: {asks}')
            rejected_bids.append(market_bid)
            print(rejected_bids)
            print(f'Rejected bids: {rejected_bids}')
            market_ask = ask
            print(f'Market ask: {market_ask}')
    # In either case, we should update the spread and union lists:
    spread = list(range(market_bid, market_ask+1))
    union = list(dict.fromkeys(asks + bids + [0, m]))
    print(f'union: {union}')
    print('------')

print(f'Trades: {trades}')
print(f'Prices: {prices}')
