import streamlit as st 
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np




    

st.title("Siphosethu")
st.subheader("bhunyenye")
st.sidebar.title('Msethwana')
name = st.text_input("What is your name ?")

if name:
    st.write(f"Hi {name}")
st.subheader("Fill in")

with st.form("please fill in"):
    st.subheader("Sethu deatails")
    name = st.text_input("What is your name dear ?")
    age = st.number_input("How old are you", min_value= 5, step=1)
    feedback = st.text_area("Give your feedback")
    submitted = st.form_submit_button("Submit")

if submitted:
    st.success(f"thank you {name}, {age}, for you feedback")
    st.write(f"You feedback: {feedback}")