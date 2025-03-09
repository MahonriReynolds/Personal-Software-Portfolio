
import java.io.File;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.awt.RenderingHints;
import javax.imageio.ImageIO;
import java.awt.Graphics2D;
import java.util.ArrayList;
import java.util.Arrays;
import java.awt.Color;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.stream.IntStream;
import java.io.BufferedInputStream;


// Object to hold files with hash values
class HashingFile {
    private final File file;
    private String hashValue;

    // Public init
    public HashingFile(File file) {
        this.file = file;
    }

    // hashValue getter
    public String getPerceptualHash() {
        return this.hashValue;
    }

    // hashValue setter
    public void setPerceptualHash(MediaHasher hasher) {
        this.hashValue = hasher.hash(this.file);
    }

    // file getter
    public File getFile() {
        return file;
    }
}

// Handler for hashing methods
class MediaHasher {
    // Keys to identify image or video files
    private static final List<String> IMAGE_EXTENSIONS = Arrays.asList("jpg", "jpeg", "png", "gif", "bmp", "webp");
    private static final List<String> VIDEO_EXTENSIONS = Arrays.asList("mp4", "mkv", "avi", "mov", "flv", "wmv");

    // Get the has for the passed file depending on file type
    public String hash(File file) {
        try {
            // Get the file name and pull off the entension
            String fileName = file.getName();
            int lastDot = fileName.lastIndexOf('.');
            String extension = (lastDot != -1 && lastDot < fileName.length() - 1) ? fileName.substring(lastDot + 1).toLowerCase() : null;

            // If it's an image extension, use this
            if (IMAGE_EXTENSIONS.contains(extension)) {
                // Just pass the file as an image directly to the hash calculation
                BufferedImage originalImage = ImageIO.read(file);
                return getPerceptualHash(originalImage);
            }

            // If it's a video file, use this
            if (VIDEO_EXTENSIONS.contains(extension)) {
                // Init a list to hold key frames
                List<BufferedImage> frames = new ArrayList<>();

                // Build a process that uses FMPEG to read out key frames
                ProcessBuilder processBuilder = new ProcessBuilder(
                    "ffmpeg", "-i", file.getAbsolutePath(),
                    "-vf", "select=eq(pict_type\\,I)",  // Select keyframes (I-frames)
                    "-vsync", "vfr",  // Variable frame rate
                    "-f", "image2pipe",
                    "-vcodec", "png",
                    "-"
                );
                // Don't let any errors here hang the program and just discard them
                processBuilder.redirectError(ProcessBuilder.Redirect.DISCARD);

                // Start the process
                Process process = processBuilder.start();
                // Read the FFMPEG output into a BufferedImage object until frames stop coming
                try (BufferedInputStream inputStream = new BufferedInputStream(process.getInputStream())) {
                    while (true) {
                        BufferedImage frame = ImageIO.read(inputStream);
                        if (frame == null) {
                            break; // No more frames
                        }
                        frames.add(frame);
                    }
                } finally {
                    // Stop the process
                    process.destroy();
                }

                // Return early if there's no frames to work with
                if (frames.isEmpty()) {
                    return null;
                }

                // Map all the frames to the hash calculation and filter out any nulls
                List<String> hashes = frames.stream()
                .map(this::getPerceptualHash)
                .filter(Objects::nonNull)  // Ensure non-null hashes
                .collect(Collectors.toList());

                // Return early if there's no hashes to work with
                if (hashes.isEmpty()) {
                    return null;
                }

                // Use XOR compilation to join the hashes
                // Init a starting point with the first hash
                String finalHash = hashes.get(0);
                // Loop through the hashes
                for (int i = 1; i < hashes.size(); i++) {
                    // Get the current hash now instead of every time in the inner loop
                    String currentHash = hashes.get(i);
                    // Start a new string to hold the XOR results
                    StringBuilder result = new StringBuilder();
                
                    // XOR each bit of the current hash with the corresponding bit of the final hash
                    for (int j = 0; j < finalHash.length(); j++) {
                        char bit1 = finalHash.charAt(j);
                        char bit2 = currentHash.charAt(j);
                        result.append(bit1 == bit2 ? '0' : '1');
                    }
                
                    // Update finalHash with the result of XOR operation
                    finalHash = result.toString();
                }
                
                // Send back the hash value
                return finalHash;
            }

        // All other paths return null
            return null;
        } catch (Exception e) {
            return null;
        }
    }

    // Calculate the hash of a given image
    private String getPerceptualHash(BufferedImage image) {
        try {
            // Create a new image, 8x8 and grayscale
            BufferedImage workingImage = new BufferedImage(8, 8, BufferedImage.TYPE_BYTE_GRAY);
            // Create a Graphics2D of the new image to handle drawing into it
            Graphics2D g2d = workingImage.createGraphics();
            // Set quality settings for the Graphics2D
            g2d.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
            // Use the Graphics2D to draw the origional image into the new 8x8 grayscale image
            g2d.drawImage(image, 0, 0, 8, 8, null);
            // The Graphics2D is no longer needed
            g2d.dispose();

            // For each pixel in the 8x8, get the red value of each
            int[][] pixels = new int[8][8];
            for (int y = 0; y < 8; y++) {
                for (int x = 0; x < 8; x++) {
                    pixels[x][y] = new Color(workingImage.getRGB(x, y)).getRed();
                }
            }

            // Get the average pixel value
            int avgPixel = Arrays.stream(pixels).flatMapToInt(Arrays::stream).sum() / 64;
            // Init a new string for the hash value
            StringBuilder hash = new StringBuilder();
            // For each pixel in the 8x8, hash out a comparison to the average pixel value
            for (int y = 0; y < 8; y++) {
                for (int x = 0; x < 8; x++) {
                    hash.append(pixels[x][y] >= avgPixel ? "1" : "0");
                }
            }
            // return the calculated hash value
            return hash.toString();
        // return null if anything went wrong
        } catch (Exception e) {
            return null;
        }
    }
}

// "Burkhard-Keller Tree" uses a distance metric to compare similar string values
class BKTree {
    // Include a root node, a locking mechanism, and memory cache
    private final BKTreeNode root;
    private final ReadWriteLock lock;
    private final ConcurrentHashMap<String, List<String>> similarityCache;

    // public init that includes the first root node
    // By seeding with the first hash, the first image found will be put in a similarity grouping 
    // regardless of if it has duplicates or not
    public BKTree(String initialHash) {
        this.root = new BKTreeNode(initialHash);
        this.lock = new ReentrantReadWriteLock();
        this.similarityCache = new ConcurrentHashMap<>();
    }

    // Method for inserting a new hash
    public void insert(String hash) {
        lock.writeLock().lock();  // Ensure only one thread modifies the tree
        try {
            root.insert(hash); // Call the insert method on the root of the tree
        } finally {
            lock.writeLock().unlock();
        }
    }

    // Find similar hashes using the distance metric mentioned earlier
    public List<String> findSimilar(String hash) {
        // Get the similar hashes
        // If none, add a new entry to the hashmap
        return similarityCache.computeIfAbsent(hash, h -> {
            List<String> results = new ArrayList<>();
            lock.readLock().lock();  // Allow concurrent reads
            try {
                root.search(hash, results); // Start a recursive search for the hashes
            } finally {
                lock.readLock().unlock();
            }
            return results;
        });
    }
}

// The individual nodes for the BKTree
class BKTreeNode {
    // Each node holds a hash, a mapping of children nodes, and a locking mechanism
    private final String hash;
    private final Map<Integer, BKTreeNode> children;
    private final ReentrantLock nodeLock;


    // public init
    public BKTreeNode(String hash) {
        this.hash = hash;
        this.children = new ConcurrentHashMap<>();
        this.nodeLock = new ReentrantLock();
    }

    // method to insert a new hash
    public void insert(String newHash) {
        // "Hamming Distance" is a calculation of how different two strings are
        int distance = hammingDistance(this.hash, newHash);
    
        // lock the node while modifications are being made
        nodeLock.lock();
        try {
            // Get the child node at the calculated distance or create one if it doesn't exist
            BKTreeNode child = children.computeIfAbsent(distance, k -> new BKTreeNode(newHash));
            
            // Insert into the correct child node only if the node has been created
            if (!child.hash.equals(newHash)) {
                child.insert(newHash);
            }
        } finally {
            // release the lock
            nodeLock.unlock();
        }
    }

    // Recursive method to search through the tree
    public void search(String query, List<String> results) {
        // Set a limit for how far to search
        int maxDistance = 5;
        // If close enough, than consider it similar
        int distance = hammingDistance(this.hash, query);
        if (distance <= maxDistance) {
            results.add(this.hash);
        }

        // This is the recursive part to search the next node
        for (int d = Math.max(0, distance - maxDistance); d <= distance + maxDistance; d++) {
            BKTreeNode child = children.get(d);
            if (child != null) {
                child.search(query, results);
            }
        }
    }

    // Calculate the hamming distance between two string values
    private int hammingDistance(String s1, String s2) {
        // Compare each position of the strings to count the mismatches
        return (int) IntStream.range(0, s1.length())
                .filter(i -> s1.charAt(i) != s2.charAt(i))
                .count();
    }
}

// Main class to handle all logic
public class DuplicateMediaFinder {
    // Get the thread count for multithreading purposes
    private static final int THREAD_COUNT = Runtime.getRuntime().availableProcessors();
    // init some structures for multithreading 
    private static final ConcurrentLinkedQueue<File> fileQueue = new ConcurrentLinkedQueue<>();
    private static final ConcurrentHashMap<String, List<HashingFile>> hashMap = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<Integer, List<HashingFile>> similarityGroups = new ConcurrentHashMap<>();
    private static BKTree bkTree;
    private static int groupCounter = 1;
    private static final Object groupLock = new Object();

    // main entry point
    public static void main(String[] args) {
        // Use default input and output if no params passed in cli
        String inputFolderPath = args.length > 0 ? args[0] : "input";
        String outputFolderPath = args.length > 1 ? args[1] : "output";

        // Turn the input folder into a File object and check it's valid
        File inputFolder = new File(inputFolderPath);
        if (!inputFolder.exists() || !inputFolder.isDirectory()) {
            System.out.println("Invalid input folder path: " + inputFolderPath);
            return;
        }

        // Turn the output folder into a File object and make if not present
        File outputFolder = new File(outputFolderPath);
        if (!outputFolder.exists()) outputFolder.mkdir();

        // Init a hasher object to access hashing operations
        MediaHasher hasher = new MediaHasher();
        // Init an executor for multithreading processes
        ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);

        // Read files recursively into the file queue
        readFilesRecursively(inputFolder, fileQueue);

        // Multithread the file hash calculations for all files in the queue
        List<Future<HashingFile>> futures = new ArrayList<>();
        while (!fileQueue.isEmpty()) {
            File file = fileQueue.poll();
            if (file != null) {
                futures.add(executor.submit(() -> {
                    HashingFile hf = new HashingFile(file);
                    hf.setPerceptualHash(hasher);
                    return hf;
                }));
            }
        }

        // Filter out the null values
        List<HashingFile> hashingFiles = futures.stream().map(f -> {
            try { return f.get(); } catch (Exception e) { return null; }
        })
        .filter(Objects::nonNull)
        .filter(hf -> hf.getPerceptualHash() != null)
        .collect(Collectors.toList());

        // Build the BK-Tree
        if (!hashingFiles.isEmpty()) {
            String firstValidHash = hashingFiles.stream()
                .map(HashingFile::getPerceptualHash)
                .filter(Objects::nonNull)
                .findFirst().orElse(null);
        
            if (firstValidHash != null) {
                bkTree = new BKTree(firstValidHash);
                
                hashingFiles.forEach(hf -> {
                    String hash = hf.getPerceptualHash();
                    if (hash != null) {
                        hashMap.computeIfAbsent(hash, k -> new ArrayList<>()).add(hf);
                        bkTree.insert(hash);
                    }
                });
            }
        }

        // Group Similar Files
        groupSimilarFiles(hashingFiles);

        // Move files into subfolders
        moveFilesToOutput(similarityGroups, outputFolder, executor);

        // Shut down the multithreading executor
        executor.shutdown();
        try {
            if (!executor.awaitTermination(10, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
        }
    }

    // Recursively pull all files out of the input folder into the file queue
    private static void readFilesRecursively(File folder, ConcurrentLinkedQueue<File> fileQueue) {
        // Start a list to hold all the files in the current folder
        File[] files = folder.listFiles();
        if (files != null) {
            // For each file, add it to the queue
            // For each folder, start another recursive search
            for (File file : files) {
                if (file.isDirectory()) {
                    readFilesRecursively(file, fileQueue);
                } else {
                    fileQueue.offer(file);
                }
            }
        }
    }

    // Collect similar files into similarity groupings
    private static void groupSimilarFiles(List<HashingFile> hashingFiles) {
        Map<String, Integer> hashToGroupMap = new ConcurrentHashMap<>();
    
        // Search the tree for each hash / add hashes in
        for (HashingFile hf : hashingFiles) {
            String hash = hf.getPerceptualHash();
            List<String> similarHashes = bkTree.findSimilar(hash);
    
            // Lookup existing group for a similar hash
            Integer groupId = null;
            for (String similarHash : similarHashes) {
                if (hashToGroupMap.containsKey(similarHash)) {
                    groupId = hashToGroupMap.get(similarHash);
                    break;
                }
            }
    
            // If no group found, create a new one
            if (groupId == null) {
                synchronized (groupLock) {
                    groupId = groupCounter++;
                    similarityGroups.put(groupId, new ArrayList<>());
                }
            }
    
            // Add current file to the group
            similarityGroups.get(groupId).add(hf);
            hashToGroupMap.put(hash, groupId);
        }
    }
    
    // Method to finally move all files into the output subfolders
    private static void moveFilesToOutput(ConcurrentHashMap<Integer, List<HashingFile>> groups, File outputFolder, ExecutorService executor) {
        // Make a subfolder for any files without similars if doesn't exist
        File originalsFolder = new File(outputFolder, "originals");
        if (!originalsFolder.exists()) originalsFolder.mkdir();
    
        // Multithread the movement of each grouping
        for (Map.Entry<Integer, List<HashingFile>> entry : groups.entrySet()) {
            List<HashingFile> groupFiles = entry.getValue();
            
            if (groupFiles.size() == 1) {
                // If only one file in the group, move it to originals subfolder
                moveFile(groupFiles.get(0), originalsFolder, executor);
            } else {
                // Otherwise, create a group folder for that grouping and move files there
                File groupFolder = new File(outputFolder, "Group_" + entry.getKey());
                if (!groupFolder.exists()) groupFolder.mkdir();
                
                for (HashingFile hf : groupFiles) {
                    moveFile(hf, groupFolder, executor);
                }
            }
        }
    }

    // Method to actually move files into their subfolders
    private static void moveFile(HashingFile hf, File destinationFolder, ExecutorService executor) {
        // Submit each movement to the multithreading executor
        executor.submit(() -> {
            try {
                File destination = new File(destinationFolder, hf.getFile().getName());
                Files.move(hf.getFile().toPath(), destination.toPath(), StandardCopyOption.REPLACE_EXISTING);
            } catch (IOException e) {
                System.err.println("Error moving file: " + hf.getFile().getName());
            }
            return null;
        });
    }
}

