import numpy as np
import pandas as pd
import pydeck as pdk
import seaborn as sns
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import plotly.figure_factory as ff


st.title('Analyze Your Uber Data')

# Upload CSV provided by Uber
uploaded_file = st.file_uploader('Choose a CSV File')
if uploaded_file is not None:
	dataframe = pd.read_csv(uploaded_file)

	# fix column to be read in as a datetime
	dataframe['Begin Trip Time'] = dataframe['Begin Trip Time'].str.slice(stop = -10)
	dataframe['Begin Trip Time'] = pd.to_datetime(dataframe['Begin Trip Time'])
	# convert to PST from UTC
	dataframe['Begin Trip Time'] = dataframe['Begin Trip Time'] + pd.Timedelta(hours = -8)

	# add a month column
	dataframe['month'] = pd.DatetimeIndex(dataframe['Begin Trip Time']).month
	month_label = {1.0: 'Jan', 2.0: 'Feb', 3.0: 'Mar', 4.0: 'April',
				   5.0: 'May', 6.0: 'June', 7.0: 'July', 8.0: 'Aug',
				   9.0: 'Sep', 10.0: 'Oct', 11.0: 'Nov', 12.0: 'Dec'}

	dataframe['day'] = dataframe['Begin Trip Time'].dt.weekday
	day_label = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}

	dataframe['hour'] = dataframe['Begin Trip Time'].dt.hour


# Output data
# Function to split pickup and dropoff address
# @st.cache_data
def separate_address(df, var, text):
    # split the data by comma, add column names
    split_address = df[var].str.split(pat = ', ', expand = True)
    df_shape = split_address.shape
    split_address.columns = ['colname' + str(i) for i in range(0, df_shape[1])]

    # drop columns that have values in columns 5+
    # logic: if record has value in 5, it must have in succeeding columns as well
    if df_shape[1] > 5:
        to_drop = split_address.notna()
        to_drop = to_drop[to_drop['colname5'] == True]
        split_address = split_address[~split_address.index.isin(to_drop.index)]
        split_address = split_address.iloc[:, 0:5]
        split_address_nona = split_address.dropna(how = 'all')
        all_missing = split_address[~split_address.index.isin(split_address_nona.index)]
    else:
        split_address_nona = split_address.dropna(how = 'all')
        all_missing = split_address[~split_address.index.isin(split_address_nona.index)]

    # clean up records with all 5 columns populated
    df_int1 = split_address_nona[~split_address_nona['colname4'].isnull()]

    # split city, full zip
    state_zip = df_int1['colname3'].str.split(' ', expand = True)
    state_zip.columns = ['state', 'zip']

    # split zip5/zip4 if it exists
    zip_split = state_zip['zip'].str.split('-', expand = True)
    if zip_split.shape[1] == 2:
        zip_split.columns = ['zip5', 'zip4']
    else:
        zip_split.columns = ['zip5']

    # assemble dataframe
    df1 = pd.concat([df_int1.drop('colname3', axis = 1),
                    state_zip.drop('zip', axis = 1),
                    zip_split], axis = 1)
    if df1.shape[1] == 7:
        df1.columns = ['address0', 'address', 'city', 'country', 'state', 'zip5', 'zip4']
    else:
        df1.columns = ['address0', 'address', 'city', 'country', 'state', 'zip5']


    # clean up records with 4 columns populated
    df_int2 = split_address_nona[~split_address_nona.index.isin(df_int1.index)]
    df_int2 = df_int2[~df_int2['colname3'].isnull()]

    # split city, full zip
    state_zip = df_int2['colname2'].str.split(' ', expand = True)
    state_zip.columns = ['state', 'zip']

    # split zip5/zip4 if it exists
    zip_split = state_zip['zip'].str.split('-', expand = True)
    if zip_split.shape[1] == 2:
        zip_split.columns = ['zip5', 'zip4']
    else:
        zip_split.columns = ['zip5']

    # assemble dataframe
    df2 = pd.concat([df_int2.drop('colname2', axis = 1),
                    state_zip.drop('zip', axis = 1),
                    zip_split], axis = 1)
    if df2.shape[1] == 7:
        df2.columns = ['address', 'city', 'country', 'empty', 'state', 'zip5', 'zip4']
    else:
        df2.columns = ['address', 'city', 'country', 'empty', 'state', 'zip5']
    df2.drop('empty', axis = 1, inplace = True)

    address_df = pd.concat([df1, df2])
    address_df.columns = text + address_df.columns
    
    return address_df

begin = separate_address(dataframe, 'Begin Trip Address', 'begin_')
end = separate_address(dataframe, 'Dropoff Address', 'end_')

df1 = pd.merge(dataframe,
			   begin,
			   how = 'left',
			   left_index = True,
			   right_index = True)
df2 = pd.merge(df1,
			   end,
			   how = 'left',
			   left_index = True,
			   right_index = True)


# Available filters
st.sidebar.subheader('Filterable Values')
product_type = st.sidebar.multiselect(
    'Product Type',
    df2['Product Type'].unique(),
    df2['Product Type'].unique()
)
order_status = st.sidebar.multiselect(
    'Trip/Order Status',
    df2['Trip or Order Status'].unique(),
    df2['Trip or Order Status'].unique()
)
country = st.sidebar.multiselect(
	'Country',
	df2['begin_country'].unique(),
	df2['begin_country'].unique()
)
country_df = df2[df2['begin_country'].isin(country)]
region = st.sidebar.multiselect(
	'Uber Defined City',
	country_df['City'].unique(),
	country_df['City'].unique()
)
region_df = country_df[country_df['City'].isin(region)]
city = st.sidebar.multiselect(
	'Pickup City',
	region_df['begin_city'].unique(),
	region_df['begin_city'].unique()
)
city_df = region_df[region_df['begin_city'].isin(city)]
zip_code = st.sidebar.multiselect(
	'Pickup Zip Code',
	city_df['begin_zip5'].unique(),
	city_df['begin_zip5'].unique()
)
zip_code_df = city_df[city_df['begin_zip5'].isin(zip_code)]
price = st.sidebar.slider(
	'Range of Price of Ride',
	zip_code_df['Fare Amount'].min(),
	zip_code_df['Fare Amount'].max(),
	15.0
)
distance = st.sidebar.slider(
	'Distance of Ride (miles)',
	zip_code_df['Distance (miles)'].min(),
	zip_code_df['Distance (miles)'].max(),
	15.0
)


# Output
# df2 has the entire address split into individual columns
df = df2[(df2['Product Type'].isin(product_type)) &
		 (df2['Trip or Order Status'].isin(order_status)) &
		 (df2['City'].isin(region)) &
		 (df2['begin_city'].isin(city)) &
		 (df2['begin_zip5'].isin(zip_code)) &
		 (df2['begin_country'].isin(country)) &
		 (df2['Fare Amount'] <= price) &
		 (df2['Distance (miles)'] <= distance)
		]

if st.checkbox('Show Raw Data'):
	st.subheader('All Data Preview')
	st.dataframe(dataframe)

if st.checkbox('Show Filtered Data'):
	st.subheader('Filtered Data Preview')
	st.dataframe(df)


# Visualizations
## Viz 1
st.subheader('Number of Pickups by Hour')
hist_values = np.histogram(
	df['Begin Trip Time'].dt.hour,
	bins = 24,
	range = (0, 24)
)[0]
st.bar_chart(hist_values)

## Viz 2
st.subheader('Distribution of Ride Cost')
fig = ff.create_distplot([df['Fare Amount']], group_labels = ['All Rides'])
st.plotly_chart(fig)

## Viz 3
st.subheader('Distribution of Ride Distance')
fig = ff.create_distplot([df['Distance (miles)']], group_labels = ['All Rides'])
st.plotly_chart(fig)

## Viz 4
ride_counts = (df['month'].value_counts()
                          .reset_index()
                          .rename(columns = {'month': 'num_of_rides',
                                             'index': 'month'})
                          .sort_values('month'))
ride_counts['month_chr'] = ride_counts['month'].map(month_label)
st.subheader('Rides per Month')

fig = px.line(ride_counts,
			  x = 'month_chr',
			  y = 'num_of_rides',
			  labels = {'month_chr': 'Month',
			  			'num_of_rides': 'Number of Rides'})
st.plotly_chart(fig, use_container_width = True)

## Viz 5
st.subheader('Rides by Day of Week')
day_counts = (df['day'].value_counts()
                       .reset_index()
                       .rename(columns = {'day': 'num_of_rides',
                                          'index': 'day'})
                       .sort_values('day'))
day_counts['day_chr'] = day_counts['day'].map(day_label)
fig = px.line(day_counts,
			  x = 'day_chr',
			  y = 'num_of_rides',
			  labels = {'day_chr': 'Day',
			  			'num_of_rides': 'Number of Rides'})
st.plotly_chart(fig, use_container_width = True)

## Viz 6
heatmap_df = df.groupby(['day', 'hour']).size().reset_index()
heatmap_df.columns = ['day', 'hour', 'counts']
heatmap_df_pivot = heatmap_df.pivot(index = 'day', columns = 'hour', values = 'counts').fillna(0)
heatmap_df_pivot.index = [*map(day_label.get, list(heatmap_df_pivot.index))]

st.subheader('Pickups by Time and Day')
fig, ax = plt.subplots()
sns.heatmap(heatmap_df_pivot, ax = ax, square = True, cbar = False, cmap = 'coolwarm')
plt.xlabel('')
plt.tight_layout()
st.write(fig)


## Maps
st.subheader('Map of Pickups')
df_map = df[['Begin Trip Lat', 'Begin Trip Lng']].dropna()
df_map.columns = ['lat', 'lon']
st.map(df_map)

# Map 2
st.pydeck_chart(pdk.Deck(
    map_style = None,
    initial_view_state = pdk.ViewState(
        latitude = 37.76,
        longitude = -122.4,
        zoom = 11,
        pitch = 50,
    ),
    layers = [
        pdk.Layer(
           'HexagonLayer',
           data = df_map,
           get_position = '[lon, lat]',
           radius = 200,
           elevation_scale = 4,
           elevation_range = [0, 1000],
           pickable = True,
           extruded = True,
        ),

    ],
))