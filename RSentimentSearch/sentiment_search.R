
# Import libraries for dashboard and api functionality
library(shiny)
library(httr)
library(jsonlite)
library(syuzhet)
library(DT)

# Typically, this would be handled securely and not hard coded.
# However, this was a dummy acount that has since been deactivated 
# so these will stay for demonstration purposes.
user_agent <- "sentiment_analysis_search_v1_by_snake_case" 
client_id <- "noG5QVOJJyJwSBXXb_B6Hw"
client_secret <- "JcEUCgZPwSrfm9y-wMUv2mHHWxpI3A"

# Send credentials to reddit api authentication endpoint
# and recieve back an access token to make regular calls
# with.
auth_response <- POST("https://www.reddit.com/api/v1/access_token", 
                      authenticate(client_id, client_secret),
                      add_headers("User-Agent" = user_agent),
                      body = list(grant_type = "client_credentials"),
                      encode = "form")

# Extract the access token from the repsonse.
access_token <- content(auth_response)$access_token

# Every subsequent call will use the same header so
# define it here for easy access.
headers <- add_headers(
  Authorization = paste("Bearer", access_token),
  "User-Agent" = user_agent
)

# This defines the shiny dashboard UI layout.
ui <- fluidPage(
  # Title the page
  titlePanel("Reddit Sentiment Analysis Search"),

  # Add small text under the title for a disclaimer.
  tags$p(
    "**Disclaimer: These results are unreliable and purely exploratory. Also, please understand that results represent the overall attitude these topics are approached from, not the general opinion of the topic. For example, 'plane crash' may read primarily positive as posts tend to talk positively about victims and should not be interpreted as Reddit being in favor of plane crashes. Or, searching a political figure may read primarily negative simply because political posts tend to be confrontational and should not be interpreted as Reddit being opposed to that political figure.",
    style = "font-size: 12px; color: #555;"
  ),
  
  # Add some custom CSS to keep elements from overlapping.
  # Keep each element in a fixed area and allow scrolling
  # within that area if needed.
  tags$style(HTML("
    .scrollable {
      overflow-y: auto;
      overflow-x: auto;
      max-height: 300px; /* Adjust this value for vertical scroll */
      max-width: 100%; /* Allow horizontal scroll */
    }
    .sidebarPanel, .mainPanel {
      max-height: 600px; /* Set max height for both panels */
      overflow-y: auto;
      overflow-x: auto;
    }
    .search-history {
      max-height: 200px; /* Limit the height of the search history section */
      overflow-y: auto;
    }
    /* Ensure layout takes up available space and both panels are aligned */
    .shiny-input-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .sidebarLayout .sidebarPanel, .sidebarLayout .mainPanel {
      flex: 1;
      max-height: 100%;
    }
  ")),

  # Add a side panel that will hold the main functionality
  # such as search input and history.
  sidebarLayout(
    sidebarPanel(
      
      # Add text input and search button.
      textInput("user_text", "Topic:", ""),
      actionButton("search_btn", "Search"),
      br(), br(),
      actionButton("stop_btn", "Stop App", class = "btn-danger"),
      br(), br(),

      # Add search history download button.
      downloadButton("download_csv", "Download Search History"),
      
      br(), br(),
      # Show search history.
      div(
        class = "search-history",
        DT::dataTableOutput("history_table")
      )
    ),
    
    # Add main panel to display individual search results.
    mainPanel(
      uiOutput("sentiment_bar"),
      verbatimTextOutput("text_output")
    )
  )
)

# This defines the server logic of the shiny dashboard.
server <- function(input, output, session) {
  # Define a reactive variable to store up to date search information.
  search_history <- reactiveVal(data.frame(
    Search_Text = character(0),
    Positive_Percentage = numeric(0),
    Negative_Percentage = numeric(0)
  ))
  
  # Get the sentiment of posts found.
  sentiment_data <- eventReactive(input$search_btn, {
    # Only make an api call when there is user input.
    req(input$user_text)

    # Define the parameters of the api query.
    params <- list(
      q = URLencode(input$user_text),
      sort = "new",
      limit = 100
    )
    # Make the call to reddit's api.
    search_response <- GET("https://oauth.reddit.com/search", headers, query = params)

    # Format the repsonse.
    parsed_data <- fromJSON(content(search_response, as = "text"))
    
    # Filter out the text contents of each post found.
    posts_found <- list()
    for (i in seq_along(parsed_data$data$children$kind)) {
      # Access 'selftext' from the 'data' column of the 'children' dataframe
      posts_found[[i]] <- parsed_data$data$children$data$selftext[i]
      
      # If no text is available, leave NULL.
      if (is.na(posts_found[[i]])) {
        posts_found[[i]] <- NULL
      }
    }
    
    # Here is the actual logic for getting the sentiments.
    sentiments <- get_sentiment(posts_found, method = "syuzhet")
    
    # Count up how many posts came back positive and negative.
    positive_count <- 0
    negative_count <- 0
    if (!is.null(posts_found)) {
      for (sentiment in sentiments) {
        if (sentiment > 0) {
          positive_count <- positive_count + 1
        } else {
          negative_count <- negative_count + 1
        }
      }
    }
    
    # Using the counts of positive and negative, get
    # the percentage of each to 2 decimal places.
    positive_percentage <- 0
    negative_percentage <- 0
    total_count <- positive_count + negative_count
    if (total_count > 0) {
      positive_percentage <- round((positive_count / total_count) * 100, 2)
      negative_percentage <- round(100 - positive_percentage, 2)
    }
    
    # Create a new row for this search.
    new_row <- data.frame(
      Search_Text = input$user_text,
      Positive_Percentage = positive_percentage,
      Negative_Percentage = negative_percentage
    )
    
    # Update the search history.
    current_history <- search_history()
    updated_history <- rbind(current_history, new_row)
    search_history(updated_history)
    
    # Return the sentiment results and percentages.
    list(sentiment_results = new_row, 
         positive_percentage = positive_percentage, 
         negative_percentage = negative_percentage, 
         posts = posts_found)
  })
  
  # Render the positive / negative percentage bar.
  output$sentiment_bar <- renderUI({
    # Get the percentages.
    percentages <- sentiment_data()

    # Define some css configuration to display both percentages
    # as two parts of one total bar.
    # Add in the actual numbers to be displayed.
    tagList(
      tags$div(
        style = "width: 100%; background-color: #ddd; border-radius: 5px; position: relative; height: 30px;",
        tags$div(
          style = paste0(
            "width: 100%; height: 100%; border-radius: 5px; text-align: center; color: white; white-space: pre;
            background: linear-gradient(to right, rgb(9, 210, 15) ", percentages$positive_percentage, "%, 
            rgb(224, 24, 24) ", percentages$positive_percentage, "%);"
          ),
          paste0(round(percentages$positive_percentage, 1), "% Positive   |  ", round(percentages$negative_percentage, 1), "% Negative")
        )
      )
    )
  })
  
  # Display the posts found.
  output$text_output <- renderText({
    paste("Posts Found:\n", paste(sentiment_data()$posts, collapse = "\n "))
  })
  
  # Display search history.
  output$history_table <- DT::renderDataTable({
    search_history()
  })
  
  # Download the search history.
  output$download_csv <- downloadHandler(
    filename = function() {
      paste("search_history_", Sys.Date(), ".csv", sep = "")
    },
    content = function(file) {
      write.csv(search_history(), file, row.names = FALSE)
    }
  )
  
  # Watch the Stop App button and quit if pressed.
  observeEvent(input$stop_btn, {
    cat("Shiny app is stopping and exiting R...\n")
    stopApp()
    Sys.sleep(1)
    q("no")
  })
}

# Use 8080 for every deployment of the dashboard.
PORT <- 8080

# Check that the dashboard can be hosted on this local address.
local_ip <- tryCatch({
  ip <- system("hostname -I", intern = TRUE)
  if (length(ip) > 0) trimws(strsplit(ip, " ")[[1]][1]) else "127.0.0.1"
}, error = function(e) "127.0.0.1")

# Double check that all local address messages have been printed.
message("\nShiny app running at:")
message("Local: http://127.0.0.1:", PORT)
message("Network: http://", local_ip, ":", PORT, "\n")

# Start the shiny dashboard and server.
shiny::runApp(list(ui = ui, server = server), host = "0.0.0.0", port = PORT)

