# Created a fantasy football draft model
# Using this tutorial https://www.fantasyfootballdatapros.com/blog/intermediate/6

# Import statements
import pandas as pd
from bs4 import BeautifulSoup as BS
import requests

# Function to create data frame from fantasypros PPR rankings
def make_adp_df(url):
    #https://www.fantasypros.com/nfl/adp/ppr-overall.php
    res = requests.get(url)
    if res.ok:
        
        soup = BS(res.content, 'html.parser')
        table = soup.find('table',{'id':'data'})
        df = pd.read_html(str(table))[0]
        #print('Output after reading the html:\n\n',df.head(),'\n')
        
        df = df[['Player Team (Bye)','POS','AVG']]
        #print('Output after filter:\n\n',df.head(),'\n')
        
        df['PLAYER'] = df['Player Team (Bye)'].apply(lambda x:' '.join(x.split()[:-2]))
        df['POS'] = df['POS'].apply(lambda x: x[:2])  
        
        df = df[['PLAYER','POS','AVG']].sort_values(by='AVG')
        #print('Final output:\n\n',df.head(),'\n')
        
        return df       

# Function to create data frame from fantasypros PPR projections
def make_projection_df(url):
    #https://www.fantasypros.com/nfl/projections/{position}.php?week=draft
    final_df = pd.DataFrame()
    
    # Each position has a different webpage, need to cycle through each
    for pos in ['rb','qb','te','wr']:
        
        res = requests.get(url.format(position=pos))
        if res.ok:
            
            soup = BS(res.content, 'html.parser')
            table = soup.find('table',{'id':'data'})
            df = pd.read_html(str(table))[0]
            
            df.columns = df.columns.droplevel(level=0)
            df['PLAYER'] = df['Player'].apply(lambda x: ' '.join(x.split()[:-1]))
            if 'REC' in df.columns:
                df['FPTS'] = df['FPTS']+df['REC']
            
            df['POS'] = pos.upper()
            
            df = df[['PLAYER','POS','FPTS']]
            final_df = pd.concat([final_df,df])
        else:
            print("Oops, sommething when wrong for ",pos,'\n',res.status_code)
            return
    
    return final_df

# Utilize above functions to actually create the data frames
BASE_URL_ADP = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"
df_adp=make_adp_df(BASE_URL_ADP)

BASE_URL_PROJ = 'https://www.fantasypros.com/nfl/projections/{position}.php?week=draft'
df_proj=make_projection_df(BASE_URL_PROJ)


# Now we will find replacement (or average) players which we will then use to determine
# how valueable other players are compared to a replacement(average) player in that postion

# Empty dictionary of positions for replacement players
replacement_players = {
    'RB':'',
    'WR':'',
    'TE':'',
    'QB':''
    }
# To find the replacement player we will take the player closest to the defined ADP below
# In the example at the time of writing this, I am taking the players from each postion
# drafted closest, but not greater than 75th overall.

AVERAGE_ADP = 75
for i, row in df_adp[:AVERAGE_ADP].iterrows():
    position = row['POS']
    player = row['PLAYER']
    replacement_players[position] = player
    
# Empty dictionary of positions for replacement values
replacement_values = {
    'RB':0,
    'WR':0,
    'TE':0,
    'QB':0    }

# Assigns replacement values based on the replacement players found
for position, player in replacement_players.items():
    replacement_values[position] = df_proj.loc[df_proj['PLAYER'] == player].values[0,-1]
    
# Creates a new data frame and calculates value over replacement (vor)
df_vor = df_proj
df_vor['VOR'] = df_vor.apply(lambda row: row['FPTS'] - replacement_values.get(row['POS']),axis=1)

# Sort by VOR and add a rank based on that sort
df_vor = df_vor.sort_values(by='VOR',ascending=False)
df_vor['VALUERANK'] = df_vor['VOR'].rank(ascending=False)


# Next we will look for sleepers (players going later in the draft than the should based on value)

# Sort and rank players in the ADP data frame
df_adp['ADPRANK'] = df_adp['AVG'].rank(method='first')

# Add ADP data to the vor data frame
df_vor = df_vor.merge(df_adp,how='left',on=['PLAYER','POS'])

# Calculate a "sleeper score" based on variance between ranks for adp (ADPRANK) and vor(VALUERANK)
df_vor['SLEEPERSCORE'] = df_vor['ADPRANK'] - df_vor['VALUERANK']

#Print statements to preview data frame
#print(df_vor.loc[df_vor['AVG'] < 100].sort_values(by='SLEEPERSCORE', ascending = False).head(15))
print("Preview of Final Data Frame:")
print(df_vor.head())

# Export data frame to excel
# Adds current date to file name so this program can be run multiple times before
# draft occurs to analyze and find trends in rank changes
excel_yn = input("Do you want to export the data frame to excel?")
if excel_yn.lower() in ["y","yes"]:
    from datetime import date
    today = str(date.today())
    df_vor.to_excel("df_vor_wSS_"+today+".xlsx") 

