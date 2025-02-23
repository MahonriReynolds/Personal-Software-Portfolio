# Overview


This script identifies duplicate / similar photos and videos in bulk. It recursively pulls image and video files from an input folder, identifies duplicate / similar photos, and presents those similarity groupings to the user in an output folder. To handle large amounts of photos, the script uses multithreading functionality. The exact use case it was designed for was the migration of multiple Google Photos collections into one collection. It reads the input folder recursively to handle the Google Takeout folder tree, and handles operations on multiple threads to account for the bulk photo inputs.

This program was primarily written to explore the basics of Java and produce a simple utility script. It looks at the use of variables, expressions, conditionals, loops, functions, classes, data structures from the java collection framework such as ArrayList and HashMap, and reading / writing to files.

[Software Demo Video](https://youtu.be/DX0d-KJS41w)

# Development Environment

- OpenJDK 21.0.6
- VSCode 1.97.2

- Java 21.0.6
- Javac 21.0.6
- Standard Java Collection Framework for 21.0.6


# Useful Websites

- [Geeks For Geeks on Hamming Distance](https://www.geeksforgeeks.org/concepts-of-hamming-distance/)
- [Geeks For Geeks on Burkhard-Keller Tree](https://www.geeksforgeeks.org/bk-tree-introduction-implementation/)
- [W3 Schools on Java Basics](https://www.w3schools.com/java/)
- [Jenkov on Concurrency In Java](https://jenkov.com/tutorials/java-concurrency/index.html)


# Future Work

- There is little to no error handling and logging.
- It could benefit from a gui to allow for easier file selection post processing.
- There are further optimizations to be made such as reducing calls to the hash value getter.
