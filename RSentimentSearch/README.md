# Overview

This R script allows the user to search recent Reddit posts for a specific topic and recieve back a sentiment analysis of the first 100 relevant posts found. The sentiment analysis is displayed as a dual colored bar with percentage labels. The user can search their history for that session and compare results in a table.

This script was written to explore the basics of the language such as its data types, loops, dataframes, and screen outputs.

[Software Demo Video](https://youtu.be/rBmw9ksu3cY)

# Development Environment

- VSCode 1.96.4
- Git 2.43.0
- R 4.3.3
    - Shiny library 1.10.0
    - Httr library 1.4.7
    - Jsonlite library 1.8.9
    - Syuzhet library 1.0.7
    - DT library 0.33

# Useful Websites

- [W3 Schools](https://www.w3schools.com/r/)
- [Geeks For Geeks](https://www.geeksforgeeks.org/shiny-r-dashboard/)
- [Reddit API Documentation](https://www.reddit.com/dev/api)

# Future Work

- Needs error handling and retry loops.
- Could use a cleaner UI with a theme.
- Especially for longer posts, sentiment analysis can be improved for more accurate results.
