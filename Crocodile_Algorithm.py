# Import the libraries we will use here.
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters.morningstar import Q1500US
import numpy as np
import time

def initialize(context):
    """
    Called once at the start of the program. Any one-time
    startup logic goes here.
    """
    # Define context variables that can be accessed in other methods of the algorithm.
    context.up_price = {} 
    context.low_price = {} 
    context.up_fractal_exists = {} 
    context.down_fractal_exists = {} 
    context.AO_index = {} 
    context.cal_AC_index = {} 
    context.AC_index = {} 
    context.amount = {} 
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.buy_stock = []
    context.month=2
    schedule_function(select_universe, date_rules.month_start(11), time_rules.market_open(minutes=2))
    schedule_function(dealwithdata, date_rules.every_day(), time_rules.market_open(hours=3,minutes=30))
    
#reset global variables
def reset_global(context):
    context.up_price = {} 
    context.low_price = {} 
    context.up_fractal_exists = {} 
    context.down_fractal_exists = {} 
    context.AO_index = {} 
    context.cal_AC_index = {} 
    context.AC_index = {} 
    context.amount = {} 
    context.buy_stock = []
    
def initial_stock_global(context,stock):
    context.up_price[stock] = 0
    context.low_price[stock] = 0
    context.up_fractal_exists[stock] = False
    context.down_fractal_exists[stock] = False 
    context.AO_index[stock] = [0] 
    context.cal_AC_index[stock] = [0]  
    context.AC_index[stock] = [0] 
    context.amount[stock] = 0 
    
def make_pipeline():

    # Factor of yesterday's close price.
    #yesterday_close = USEquityPricing.close.latest
     
    base_universe = Q1500US()

    # Factor of yesterday's close price.
    yesterday_close = USEquityPricing.close.latest
     
    pipe = Pipeline(
        screen = base_universe,
        columns = {
            'close': yesterday_close,
        }
    )
    return pipe
    
    #close all positions after a period
def reset_position(context):
    for stock in context.buy_stock:
        if context.portfolio.positions[stock].amount != 0:
            order_target(stock,0)
            log.info("sell %s for reset position"%stock)
#select the pool of buystock
def select_universe(context, data):
    #reselect every three month
    if context.month<2:
        context.month+=1
        return
    context.month=0
    #reset global variables
    context.output = pipeline_output('my_pipeline')
    context.stock = context.output.index
    reset_position(context)
    reset_global(context)
    hist = data.history(context.stock, 'close', 52, '1d')
    for stock in context.stock:
        if is_sleeping_alligator(stock,hist,30):
            context.buy_stock.append(stock)
            #initialize the global variables of this stock
            initial_stock_global(context, stock)
    print context.buy_stock
    return None

#sleeping crocodile
def is_sleeping_alligator(stock,hist,nday):
    for i in range(nday):
        if is_struggle(stock,hist,i) == False:
            return False
    return True

#whether the moving average are tangling
def is_struggle(stock,hist,delta):
    blue_line = hist[stock][-1-21-delta:-1-8-delta].mean()
    red_line = hist[stock][-1-13-delta:-1-5-delta].mean()
    green_line = hist[stock][-1-8-delta:-1-3-delta].mean()
    if abs(blue_line/red_line-1)<0.02 and abs(red_line/green_line-1)<0.02:
        return True
    else:
        return False

#find the fractal(up or down)
def is_fractal(context,stock,direction,data):
    hist = data.history([stock], direction, 7, '1d')
    if direction == 'high'\
    and hist[stock][2] > hist[stock][0]\
    and hist[stock][2] > hist[stock][1]\
    and hist[stock][2] > hist[stock][3]\
    and hist[stock][2] > hist[stock][4]:
        context.up_price[stock] = hist[stock][2]
        return True
    elif direction == 'low'\
    and hist[stock][2] < hist[stock][0]\
    and hist[stock][2] < hist[stock][1]\
    and hist[stock][2] < hist[stock][3]\
    and hist[stock][2] < hist[stock][4]:
        context.low_price[stock] = hist[stock][2]
        return True
    return False

#whether it's a effective fractal
def is_effective_fractal(context,stock,direction,data):
    if is_fractal(context,stock,direction,data):
        hist = data.history([stock], 'close', 17, '1d')
        red_line = hist[stock][-1-13-3:-1-5-3].mean()
        if direction == 'high':
            if context.up_price[stock] > red_line:
                context.up_fractal_exists[stock] = True
            else:
                context.up_fractal_exists[stock] = False
        elif direction == 'low':
            if context.low_price[stock] < red_line:
                context.down_fractal_exists[stock] = True
            else:
                context.down_fractal_exists[stock] = False

#calculate AO index
def AO_index(context,stock,data):
    hist1 = data.history([stock], 'high', 50, '1d')
    hist2 = data.history([stock], 'low', 50, '1d')
    for AON in [8,7,6,5,4,3,2,1,0]:
        high_point1 = []
        low_point1 = []
        five_ave=0
        thirtyfour_ave=0
        for i in range(5):
            high_point1.append(hist1[stock][-i-2-AON])
        for j in range(5):
            low_point1.append(hist2[stock][-i-2-AON])
        five_ave=(np.array(high_point1).mean()+np.array(low_point1).mean())/2
        high_point2 = []
        low_point2 = []
        for i in range(34):
            high_point2.append(hist1[stock][-i-2-AON])
        for j in range(34):
            low_point2.append(hist2[stock][-i-2-AON])
        thirtyfour_ave=(np.array(high_point2).mean()+np.array(low_point2).mean())/2    
        context.AO_index[stock].append(five_ave-thirtyfour_ave)
    

#calculate AC
def AC_index(context,stock,data):
    AO_index(context,stock,data)
    for i in [4,3,2,1,0]:
        if i==0:
            context.AC_index[stock].append(context.AO_index[stock][-1] - np.array(context.AO_index[stock][-5:]).mean())
        else:
            context.AC_index[stock].append(context.AO_index[stock][-1-i] - np.array(context.AO_index[stock][-5-i:-i]).mean())

#whether the index is going up
def is_up_going(alist,n):
    if len(alist) < n:
        return False
    for i in range(n-1):
        if alist[-(1+i)] <= alist[-(2+i)]:
            return False
    return True

#whether the index is going down
def is_down_going(alist,n):
    if len(alist) < n:
        return False
    for i in range(n-1):
        if alist[-(1+i)] >= alist[-(2+i)]:
            return False
    return True

#breaking fractal
def active_fractal(context,stock,direction,data):
    close_price = data.history(stock, 'close', 1,'1d')
    close_price = close_price[0]
    if direction == 'up' and close_price > context.up_price[stock]:
        return True
    elif direction == 'down' and close_price < context.low_price[stock]:
        return True
    return False

#set initial position
def set_initial_position(stock,context,data):
    close_price = data.history([stock],'close', 2,'1d')
    close_price = close_price[stock][0]
    context.amount[stock] = context.portfolio.cash/close_price/len(context.buy_stock)*8
    order(stock, context.amount[stock])
    print("buying", context.amount[stock], "of", stock)
    context.down_fractal_exists[stock] = False

#close position for this stock
def sell_all_stock(stock,context):
    order_target(stock,0)
    log.info("selling %s"%stock)
    context.up_fractal_exists[stock] = False

#add position or cut position
def adjust_position(stock,context,position):
    order(stock,context.amount[stock]*position)
    print("adjust position buying ", context.amount[stock]*position," of ",stock)

#def security_return(context,days,security_code,data):
    #hist1 = data.history([security_code], 'close', days + 1, '1d')
    #security_returns = (hist1[security_code][-1]-hist1[security_code][0])/hist1[security_code][0]
    #return security_returns

#def conduct_nday_stoploss(context,security_code,data,days,bench):
    #if  security_return(context,days,security_code,data)<= bench:
        #for stock in context.buy_stock:
            #if context.portfolio.positions[stock].amount != 0:
                #order_target(stock,0)
        #log.info("Sell all for systematic risk")
        #return True
    #else:
        #return False

# calculate the accumulate return of the security
def security_accumulate_return(context,data,stock):
    current_price = data.current(stock,"price")
    cost = context.portfolio.positions[stock].cost_basis
    if cost != 0:
        return (current_price-cost)/cost
    else:
        return None

# stop loss
def conduct_accumulate_stoploss(context,data,stock,bench):
    if security_accumulate_return(context,data,stock) != None\
    and security_accumulate_return(context,data,stock) < bench:
        order_target_value(stock,0)
        log.info("Sell %s for stoploss" %stock)
        return True
    else:
        return False

# stop win
def conduct_accumulate_stopwin(context,data,stock,bench):
    if security_accumulate_return(context,data,stock) != None\
    and security_accumulate_return(context,data,stock) > bench:
        order_target_value(stock,0)
        log.info("Sell %s for stopwin" %stock)
        return True
    else:
        return False

def dealwithdata(context,data):
    #context.SP500=sid(8554)
    #if conduct_nday_stoploss(context,context.SP500,data,3,-0.03):
        #return
    for stock in context.buy_stock:
        
        if conduct_accumulate_stopwin(context,data,stock,0.3)\
        or conduct_accumulate_stoploss(context,data,stock,-0.1):
            print("conduct stop success")
            return
        
        context.AO_index[stock]=[]
        context.AC_index[stock]=[]
        AC_index(context,stock,data)
        
        if context.portfolio.positions[stock].amount == 0:
            close_price = data.history([stock], 'close', 5, '1d')
            
            is_effective_fractal(context,stock,'high',data)
            
            if context.up_fractal_exists[stock]:
                if active_fractal(context,stock,'up',data):
                    if is_up_going(context.AO_index[stock],3)\
                    and is_up_going(context.AC_index[stock],3)\
                    and is_up_going(close_price[stock],2):
                        set_initial_position(stock,context,data)
        
        else:
           
            is_effective_fractal(context,stock,'low',data)
            
            if context.down_fractal_exists and active_fractal(context,stock,'down',data):
                sell_all_stock(stock,context)
                return
            
            close_price = data.history([stock], 'close', 5, '1d')
            if is_up_going(context.AO_index[stock],5)\
            and is_up_going(context.AC_index[stock],5)\
            and is_up_going(close_price[stock],2):
                adjust_position(stock,context,0.2)
            
            if is_down_going(context.AO_index[stock],3)\
            and is_down_going(context.AC_index[stock],3)\
            and is_down_going(close_price[stock],2):
                adjust_position(stock,context,-0.2)

   