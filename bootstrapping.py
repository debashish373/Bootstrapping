import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
from dateutil.relativedelta import *
import warnings
warnings.filterwarnings('ignore')
#Creating an OIS Discount Curve

##########################
##########################

#Overnight Index Swap

#Curves 400 USD Cashflow CSA Curve
    # 42 USD OIS
    # 133 EUR OIS
    # 92 EUR vs USD Basis
    
#   Z(0,ti)=[1-{summation j=1 to i-1 (T*Xj*Z(0,tj))}] / [1+T*Xi-1]
    
##########################
##########################


#Single Curve Stripping
#######################   
        
EUR_OIS=pd.read_excel(r'../XCCY/MarketData/EUR_OIS.xlsx')[['ID','PX']].rename(columns={'ID':'Tenor'})
USD_OIS=pd.read_excel(r'../XCCY/MarketData/USD_OIS.xlsx')[['ID','PX']].rename(columns={'ID':'Tenor'})      

dict_={'D':1,'W':7,'M':30,'Y':360}
EUR_OIS['Days1']=EUR_OIS.Tenor.apply(lambda x: x[:-1]).astype('int')
EUR_OIS['Days2']=EUR_OIS.Tenor.apply(lambda x: dict_.get(x[-1]))
EUR_OIS['DC']=EUR_OIS['Days1']*EUR_OIS['Days2']

USD_OIS['Days1']=USD_OIS.Tenor.apply(lambda x: x[:-1]).astype('int')
USD_OIS['Days2']=USD_OIS.Tenor.apply(lambda x: dict_.get(x[-1]))
USD_OIS['DC']=USD_OIS['Days1']*USD_OIS['Days2']

#Bootstrapping the EUR OIS Curve!
def bootstrap(df):
    disc=[]
    zero=[]
    disc.append(1/(1+((1/360)*df.PX[0]/100)))
    #zero.append(-np.log(disc[0])/(1/360))
    df['tou']=(df['DC']-df['DC'].shift(1))/360
    df['tou'].iloc[0]=df['DC'].iloc[0]/360
    
    for i in range(0,len(df)-1):
        tou=df.loc[i+1,'tou']
        s=df.loc[i+1,'PX']/100
        #days_zero=df.loc[i+1,'DC']/360
        #zero_=[a*-1 for a in zero]
        #zero.append((-1/days_zero)*np.log((1-s*np.dot(df.tou[0:i+1],np.exp(zero_)))/(1+s*tou)))
        disc.append((1-s*np.dot(df.tou[0:i+1],disc))/(1+s*tou))
        
        
    df['DF']=disc
    df['ZR']=-np.log(df['DF'])/(df['DC']/360)
    df['ZR']=df['ZR']*100
    
    return df[['DF','ZR']]

EUR_OIS[['DF','ZR']]=bootstrap(EUR_OIS.copy())
USD_OIS[['DF','ZR']]=bootstrap(USD_OIS.copy())

EUR_OIS['Year']=EUR_OIS['DC']/360
USD_OIS['Year']=USD_OIS['DC']/360



#Dual Curve Stripping
#####################

EURIBOR_3m=pd.read_excel(r'../XCCY/MarketData/EURIBOR_3m.xlsx')[['ID','PX']].rename(columns={'ID':'Tenor','PX':'PX_3m'})

EURIBOR_3m['Days1']=EURIBOR_3m.Tenor.apply(lambda x: x[:-1]).astype('int')
EURIBOR_3m['Days2']=EURIBOR_3m.Tenor.apply(lambda x: dict_.get(x[-1]))
EURIBOR_3m['DC']=EURIBOR_3m['Days1']*EURIBOR_3m['Days2']

EURIBOR_3m=pd.merge(EURIBOR_3m,EUR_OIS[['Tenor','DF','PX']],on='Tenor',how='left').dropna(subset=['PX']).reset_index(drop=True).dropna(subset=['PX_3m']).reset_index(drop=True)

def dual_curve(df):
    forward=[]
    forward.append(df.PX_3m[0]/100)
    df['tou']=(df['DC']-df['DC'].shift(1))/360
    df['tou'].iloc[0]=df['DC'].iloc[0]/360
    
    for i in range(0,len(df)-1):
        X=(df.PX_3m[i+1]/100)*np.dot(df.tou[0:i+2],df.DF[0:i+2])
        Y=np.dot(df.DF[0:i+1],forward*df.tou[0:i+1])
        forward.append((X-Y)/(df.DF[i+1]*df.tou[i+1]))
    
    df['Forward']=forward
    df['Forward']=df['Forward']*100
    return df[['Tenor','Forward']]

temp1=pd.DataFrame()
temp1[['Tenor','Forward']]=dual_curve(EURIBOR_3m.copy())
EUR_OIS=pd.merge(EUR_OIS,temp1,on='Tenor',how='left')

USD_3m=pd.read_excel(r'../XCCY/MarketData/USD_3m.xlsx')[['ID','PX']].rename(columns={'ID':'Tenor','PX':'PX_3m'}).dropna(subset=['PX_3m'])
USD_3m['Days1']=USD_3m.Tenor.apply(lambda x: x[:-1]).astype('int')
USD_3m['Days2']=USD_3m.Tenor.apply(lambda x: dict_.get(x[-1]))
USD_3m['DC']=USD_3m['Days1']*USD_3m['Days2']
USD_3m=pd.merge(USD_3m,USD_OIS[['Tenor','DF','PX']],on='Tenor',how='left').dropna(subset=['PX']).reset_index(drop=True).dropna(subset=['PX_3m']).reset_index(drop=True)

temp2=pd.DataFrame()
temp2[['Tenor','Forward']]=dual_curve(USD_3m.copy())
USD_OIS=pd.merge(USD_OIS,temp2,on='Tenor',how='left')

#Taking care of the USD EUR Basis Spread
##########################################
Basis=pd.read_excel(r'../XCCY/MarketData/Basis.xlsx')[['ID','PX']].rename(columns={'ID':'Tenor','PX':'Basis'})


EUR_OIS_=EUR_OIS.dropna(subset=['Forward']).reset_index(drop=True)
EUR_OIS_=pd.merge(EUR_OIS_,Basis,on='Tenor',how='left').dropna(subset=['Basis']).reset_index(drop=True)
EUR_OIS_=pd.merge(EUR_OIS_,USD_3m[['Tenor','PX']].rename(columns={'PX':'PX_USD'}),on='Tenor',how='left').dropna(subset=['PX_USD']).reset_index(drop=True)
EUR_OIS_=pd.merge(EUR_OIS_.rename(columns={'Forward':'Forward1'}),USD_OIS[['Tenor','Forward']].rename(columns={'Forward':'Forward2'}),on='Tenor',how='left')#.rename(columns={'Forward_x':'Forward1','Forward_y':'Forward2'})

def basis(df):
    df['tou']=(df['DC']-df['DC'].shift(1))/360
    df['tou'].iloc[0]=df['DC'].iloc[0]/360
    dollar_disc=[]
    X0=(df.DF[0]+(df.DF[0]*(df.Forward1[0]/100+df.Basis[0]/10000)*df.tou[0]))/(1+(df.PX_USD[0]/100)*df.tou[0])
    dollar_disc.append(X0)
    
    for i in range(0,len(df)-1):
        X=df.DF[i+1]+np.dot(df.DF[0:i+2],(df.Forward1[0:i+2]/100+df.Basis[0:i+2]/10000)*df.tou[0:i+2])
        Y=(df.PX_USD[i+1]/100)*(np.dot(dollar_disc[0:i+1],df.tou[0:i+1]))
        dollar_disc.append((X-Y)/(1+(df.PX_USD[i+1]/100)*df.tou[i+1]))


    df['Dollar_DF_DC']=dollar_disc
    df['Dollar_ZR_DC']=-np.log(df['Dollar_DF_DC'])/(df['DC']/360)
    df['Dollar_ZR_DC']=df['Dollar_ZR_DC']*100
    return df[['Dollar_DF_DC','Dollar_ZR_DC']]

def basis_mod(df):
    df['tou']=(df['DC']-df['DC'].shift(1))/360
    df['tou'].iloc[0]=df['DC'].iloc[0]/360
    dollar_disc=[]
    X0=(df.DF[0]+(df.DF[0]*(df.Forward1[0]/100+df.Basis[0]/10000)*df.tou[0]))/(1+(df.Forward2[0]/100)*df.tou[0])
    dollar_disc.append(X0)
    
    for i in range(0,len(df)-1):
        X=df.DF[i+1]+np.dot(df.DF[0:i+2],(df.Forward1[0:i+2]/100+df.Basis[0:i+2]/10000)*df.tou[0:i+2])
        Y=np.dot(dollar_disc[0:i+1],(df.Forward2[0:i+1]/100)*df.tou[0:i+1])
        dollar_disc.append((X-Y)/(1+df.Forward2[i+1]/100*df.tou[i+1]))


    df['Dollar_DF_DC']=dollar_disc
    df['Dollar_ZR_DC']=-np.log(df['Dollar_DF_DC'])/(df['DC']/360)
    df['Dollar_ZR_DC']=df['Dollar_ZR_DC']*100
    return df[['Dollar_DF_DC','Dollar_ZR_DC']]


EUR_OIS_[['Dollar_DF_DC','Dollar_ZR_DC']]=basis_mod(EUR_OIS_.copy())
EUR_OIS_=pd.merge(EUR_OIS_,USD_OIS[['Tenor','ZR']].rename(columns={'ZR':'Dollar_ZR_SC'}),on='Tenor',how='left')
