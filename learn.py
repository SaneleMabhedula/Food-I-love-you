import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.write("**Hello world**")
x = st.text_input("How old are you")


if x:
    try:
        age = int(x)
        birth_year = 2025 - age
        st.write(f"your bith year is {birth_year}")
    except ValueError:
        st.write("you did not add your age ")

igama = st.text_input(" Bhala igama lakho kunye nafani")
if igama:
    st.write(f"igama lakho ungu: {igama}")
iminyaka = st.text_input("mingaphi iminyaka yakho ?")

if iminyaka:
    try: 
        lungisa = int(iminyaka)
        nyaka = 2025 - lungisa
        st.write(f" Wazalwa ngonyaka wama: {nyaka}")
    except ValueError:
        st.write("sicela ufake iminyaka yakho !")

col1, col2 = st.columns(2)
with col1:
    st.write(igama)
    
st.sidebar.title("***Isixhosa version***")
name =  st.sidebar.text_input("**Faka igama lakho** ")
if name:
    st.sidebar.write("Mholweni 👋", name + " \n sicela ukuba ugcwalise inkcukacha ezifunekayo apha ngezantsi")
st.sidebar.selectbox("**khetha isimni sakho**", ["Ms", "Mr"])
st.sidebar.date_input("**Faka idate**")
st.sidebar.text_area("Qaphela wonke amagama afakwe apha enziwe ngezizathu\n sicela uze uchule kwaye unonophele ekwenzeni kwakho")

st.te