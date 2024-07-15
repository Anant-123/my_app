import streamlit as st

# Set the title of the app
st.title("Simple Text Display App")

# Create a text input widget
user_text = st.text_input("Enter some text:")

# Display the entered text
if user_text:
    st.write("You entered:")
    st.write(user_text)

# Optionally, add a button to clear the input
if st.button("Clear"):
    st.text_input("Enter some text:", value="", key="new")
