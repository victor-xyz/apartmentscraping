# -*- coding: utf-8 -*-
"""
Python Scraper for aparmentfinder.com
"""
from bs4 import BeautifulSoup
import os
import requests
import time
import pandas as pd
import numpy as np

def get_city_data(soupobj, itemlist):
    '''
    Take in soup obj, and dataframe, return dict with relevant data for city
    '''
    for column, x in zip(['walking','biking','transit'], soupobj.find_all('div', {"id": "statusHud"})):
        y = x.find('div', class_='circle-prog-bar').attrs.get("data-value")
        itemlist[column] = int(y)
    
        
    return None

def gather_page(soupobj):
    '''
    Take in soup object return list with every
    name, address, price, rating of every entry on the page
    '''
    data = []
    for x in soupobj.find_all('div', class_='infoContainer'):
        row={}
        row['name'] = x.find('a').text.strip()
        row['link'] = x.find('a').attrs.get('href')
        row['address'] = x.find('address').text.strip()
        pricetuple = clean_price_range(x.find('span', class_='altRentDisplay').text.strip())
        row['price_low'] = pricetuple[0]
        row['price_high'] = pricetuple[1]
        temp_text=x.find('div', class_='apartmentRentRollupContainer').text.replace('\r\n','')
        row['available'] = temp_text[temp_text.find('|')+1:].strip()
        data.append(row)
    return data

def max_page_range(soupobj):
    try:
        text = soupobj.find('span', class_='pageRange').text.strip()
        return(int(text.split()[-1]))
    except:
        return(1)
    
def clean_price_range(string):
    '''
    Transforms a string representing a price into an int
    '''
    if not '$' in string:
        return (None,None)
    elif '-' in string:
        clean = string.replace('$', '').replace(',','').replace('-','').split()
        return (int(clean[0]), int(clean[1]))
    else:
        clean = string.replace('$', '').replace(',','')
        return (int(clean),int(clean))

def make_request(url):
    time.sleep(0.2)
    try:
        result = requests.get(url,
                          headers={"User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 12871.102.0) \
                               AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36"})
    except Exception as e:
        print(e)
        return(-1)
    
    return BeautifulSoup(result.content)

def gather_all_page(url):
    '''
    url is the 1st page for some city. scrape data from every page for that city
    '''
    total_list = []
    
    soup = make_request(url)
    if soup == -1:
        print('Error for: ' + url)
        return None
    max_page = max_page_range(soup)
    
    data = gather_page(soup)
    total_list += data
    for i in range(1,max_page):
        page_num = i+1
        current_url = url+'Page'+str(page_num)
        
        soup = make_request(current_url)
        pagelist = gather_page(soup)
        total_list += pagelist
    return total_list


def get_travel_stats(city, state, itemlist):
    url_city = city.replace(' ', '-')
    url_state = state.replace(' ','-')
    url = f"https://www.apartmentfinder.com/{url_state}/{url_city}-Apartments/Studio/Page1"
    
    soup = make_request(url)
    get_city_data(soup, itemlist)
    return None

def gather_pop_data(url='https://worldpopulationreview.com/us-cities'):
    '''
    gather data from worldpopulationreview.com, return information in
    a dataframe
    '''
    soup_obj=soup_obj = make_request('https://worldpopulationreview.com/us-cities')
    data=[]
    for tr in soup_obj.find('tbody').find_all('tr'):
        row = {}
        for column,td in zip(['Rank', 
                        'Name',
                        'State',
                        '2022 pop',
                        '2010 Census',
                        'Change',
                        'Density(mi2)',
                        'Area(mi2)'], tr.find_all('td')):
            row[column] = td.text.strip()
        curr_city = row['Name']
        curr_state = row['State']
        get_travel_stats(curr_city, curr_state, row)

        data.append(row)

    pop_df = pd.DataFrame(data)
    return pop_df

def create_pop():
    pop_df = gather_pop_data()
    pop_df['2022 pop'] = pop_df['2022 pop'].str.replace(',','').astype(int)
    pop_df['2010 Census'] = pop_df['2010 Census'].str.replace(',','').astype(int)
    pop_df['Density(mi2)'] = pop_df['Density(mi2)'].str.replace(',','').astype(int)
    pop_df['Area(mi2)'] = pop_df['Area(mi2)'].str.replace(',','').astype(float)
    pop_df.to_csv('populationdata_df.csv',index=False)
    return pop_df

if __name__=='__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape data from apartmentfinder.com')
    parser.add_argument('--type', help='enter "Studio" or "1-Bedroom"')
    
    try:
        args=parser.parse_args()
        if not args.type in set(['Studio', '1-Bedroom']):
            ap_type = 'Studio'
        else:
            ap_type = args.type

        pop_df = create_pop()
        
        full_dataset = []

        for city,state in zip(pop_df['Name'], pop_df['State']):
            url_city = city.replace(' ', '-')
            url_state = state.replace(' ','-')
            url = f"https://www.apartmentfinder.com/{url_state}/{url_city}-Apartments/{ap_type}/"
            city_list = gather_all_page(url)
            city_df = pd.DataFrame(city_list)
            city_df['city'] = city
            city_df['state'] = state
    
            city_df.to_csv(f"{url_state}_{url_city}.csv", index=False)
            full_dataset.append(city_df)

        final_df = pd.concat(full_dataset)
        final_df.to_csv('final_dataset.csv',index=False)
    except Exception as e:
        print(e)
        print('Unable to scrape data')
