from quantopian.pipeline import Pipeline, CustomFilter
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.factors import Latest
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data.psychsignal import aggregated_twitter_withretweets_stocktwits as st
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.filters import Q1500US
import numpy as np

def initialize(context):
    print("Attempting To Initialize")
    context.oo = 0
    context.max_leverage = 0.0
    context.securities_in_results = []
    attach_pipeline(custom_pipe(context), 'custom_pipe') 

    '''
    Hypothesis:
    small cap equities with a bullish sentiment pop will continue upward overnight

    Initialize Schedule:
    --------:---------------:------------
    time    : function      : description
    --------:---------------:------------
    9:30 am : sell          : place limit orders for all positions in pipeline (.98 threshold)
    2:29 pm : cancel_orders : cancels all open orders that have not been filled
    2:30 pm : buy           : place proportional orders (1/n) for each security in your current pipeline universe
    3:29 pm : cancel_orders : 
    3:30 pm : buy_2         : retry to place proportional orders (1/n) for each position in positions held with new price data
    4:00 pm : cancel_orders : 
    --------:---------------:------------
    
    Possible improvements:
     - is as_of date for sentiment utilized correctly?
     - Long only (meant for use on RH), could long/short lower beta?
     - Use limit orders?
    '''

    # run sell function everyday at 9:30 am
    schedule_function(sell, date_rules.every_day(), time_rules.market_open()) #open sell orders

    # run cancel_order function everyday at 2:29 pm (91 min before market close)
    schedule_function(cancel_orders, date_rules.every_day(), time_rules.market_close(minutes = 91)) 

    # run buy function everyday at 2:30 pm 
    schedule_function(buy, date_rules.every_day(), time_rules.market_close(minutes = 90)) #open buy orders

    # run cancel_order function everyday at 3:29 pm
    schedule_function(cancel_orders, date_rules.every_day(), time_rules.market_close(minutes = 31)) #close buy orders

    # run buy_2 function everyday at 3:30 pm
    schedule_function(buy_2, date_rules.every_day(), time_rules.market_close(minutes = 30)) #open buy

    # run cancel_order function everyday at 4:00 pm
    schedule_function(cancel_orders, date_rules.every_day(), time_rules.market_close())

    # no commission on RH
    set_commission(commission.PerShare(cost=0.0, min_trade_cost=0.0))
    
    context.longs = []
    context.S = []
    context.B = []
    
    print("Initialization Successful")
        
def custom_pipe(context):
    pipe = Pipeline()
    # sma_bear_7 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=7)
    # sma_bull_7 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=7)
    # sma_bear_6 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=6)
    sma_bull_6 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=6)
    # sma_bear_5 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=5)
    sma_bull_5 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=5)
    # sma_bear_4 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=4)
    sma_bull_4 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=4)
    # sma_bear_3 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=3)
    sma_bull_3 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=3)
    # sma_bear_2 = SimpleMovingAverage(inputs = [st.bearish_intensity], window_length=2)
    sma_bull_2 = SimpleMovingAverage(inputs = [st.bullish_intensity], window_length=2)
    bull_1 = st.bullish_intensity.latest
    bear_1 = st.bearish_intensity.latest
    volume = USEquityPricing.volume.latest
    pipe.add(st.bullish_intensity.latest, 'bullish_intensity')
    pipe.add(st.bearish_intensity.latest, 'bearish_intensity')
    #pipe.add(st.bear_scored_messages.latest, 'bear_scored_messages')
    #pipe.add(st.bull_scored_messages.latest, 'bull_scored_messages')
    pipe.add(st.total_scanned_messages.latest, 'total_scanned_messages') 
    #pipe.set_screen(my_sid_filter & (0.9*sma_bull_45 > sma_bear_45) & (st.total_scanned_messages.latest >= 10) ) 
    total_scan = st.total_scanned_messages.latest
    pricing = USEquityPricing.close.latest
    pipe.set_screen(
        (3.20 < pricing < 5.00)&\
        (volume>1000000)&\
        (bull_1 > sma_bull_2 < sma_bull_3  < sma_bull_4 < sma_bull_5 < sma_bull_6 > 0)&\
        (total_scan >= 10)&\
        (bull_1 > 0)
        #(bull_1 > bear_1)
    ) 
    #pipe.set_screen(my_sid_filter & (sma_10 > sma_50) ) 
    return pipe

def before_trading_start(context,data): 
    print("Before Trading Start")
    context.B = []
    context.S = []
    context.results = pipeline_output('custom_pipe')
    context.securities_in_results = []
    
    context.longs = []
    for s in context.results.index:
        if data.can_trade(s):
            context.longs.append(s)
    
def sell (context, data):
    print("closeing positions")
    PricingData = data.current(context.portfolio.positions.keys(),'price')
    for sec in context.portfolio.positions:
        if sec not in context.B:
            limit = PricingData[sec]
            try:
                # order_target_percent(sec,0,style = LimitOrder(0.98*limit))
                order_target_percent(sec,0)

                context.S.append(sec)
            except:
                order_target_percent(sec,0)
                context.S.append(sec)
            
def buy (context, data): 
   
    context.results = pipeline_output('custom_pipe')
    context.securities_in_results = []
    
    for s in context.results.index:
        context.securities_in_results.append(s) 
    context.longs= []
    if len(context.securities_in_results) > 0.0:                    
        for sec in context.securities_in_results:
            if data.can_trade(sec):
                context.longs.append(sec)
    count = 0
    for sec in context.portfolio.positions:
        if sec not in context.longs:
            count += 1

    #if len(context.longs) < 15:
    #    context.longs = []
    PricingData = data.current(context.longs,'price')
    for sec in context.longs:
        if sec not in context.S:
            limit = PricingData[sec]
            # order_target_percent(sec, 1.0/len(context.longs), style = LimitOrder(limit) )
            order_target_percent(sec, 1.0/len(context.longs))
            context.B.append(sec)

def buy_2 (context, data):
    hold = []
    if len(context.portfolio.positions) >= 0: # if you have positions in securities 
    #if len(context.portfolio.positions) >= 15:
        for sec in context.portfolio.positions:
            hold.append(sec)
        PricingData = data.current(hold,'price')
        for sec in context.portfolio.positions:
            limit = PricingData[sec]
            try:
                # order_target_percent(sec, 1.0/len(context.portfolio.positions), style = LimitOrder(limit) )
                order_target_percent(sec, 1.0/len(context.portfolio.positions))
            except:
                pass
           
def kill_open_orders(context, data):  
    for sec, orders in get_open_orders().iteritems():  
        for oo in orders:  
            log.info("X CANCELED {0:s} with {1:,d} / {2:,d} filled"\
                     .format(sec.symbol,  oo.filled, oo.amount))  
            cancel_order(oo)  
    return

def has_orders(context, data):  
    # Return true if there are pending orders.  
    has_orders = False  
    for sec in context.longs:  
        orders = get_open_orders(sec)  
        if orders:  
            #for oo in orders:  
                #message = 'Open order for {amount} shares in {stock}'  
                #message = message.format(amount=oo.amount, stock=sec)  
                #log.info(message)

            has_orders = True  
    return has_orders  

def cancel_orders (context, data):
    while has_orders(context, data):  
        kill_open_orders(context, data)  
        print('WARN: KilledOO: TicksOfOpenOrders= ', context.oo)  
        return  
    else:
        context.oo = 0
        
# slows it way down        
# def handle_data (context, data): 
#     if context.account.leverage > context.max_leverage:
#         context.max_leverage = context.account.leverage
#     record(Leverage = context.account.leverage,
#            pos=len(context.portfolio.positions),
#            resutls=len(context.securities_in_results),
#            max_leverage = context.max_leverage,
#           )