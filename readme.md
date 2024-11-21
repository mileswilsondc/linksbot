# Linksbot
A monolithic project that acts as a live RSS newswire and (eventually) web crawler for news content. A flask interface allows for simple interactive classification into `relevant` and `irrelevant`, that can be fed into a neural network to provide a daily relevant top 6.

This is an automation project that mimics GGWash's Breakfast Links newsletter, which has a somewhat narrow focus on transit and housing news in the Washington DC area. Everything flows from that use-case.

# Execution
Run `app.py` with the environment variable `SECRET_KEY` set to a secret Flask key.
