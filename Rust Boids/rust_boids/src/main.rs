// Use for key grabs and terminal manipulations
use crossterm::{
    event::{self, KeyCode, KeyEvent},
    terminal,
    ExecutableCommand,
    cursor,
};
// Use std write out and timing functionality
use std::{
    io::{self, Write},
    time::{Duration, Instant}, 
    error::Error,
    thread::sleep
};
// Use rand for boid placement
use rand::Rng; 

// Struct for the 2d grid of characters, colors representing the terminal
struct Grid {
    rows: usize,
    cols: usize,
    data: Vec<Vec<(char, String)>>
}

// Implement grid with fillers and method to display
impl Grid {
    // Auto fill new grid with empty spaces
    fn new(rows: usize, cols: usize) -> Self {
        let mut data = Vec::with_capacity(rows);

        for _ in 0..rows {
            // Initialize each row with empty cells
            let row = vec![
                (' ', String::new())  // Default symbol is space, default color is empty
            ; cols];
            data.push(row);
        }

        Grid { rows, cols, data }
    }  
    
    // Helper function for the boid's symbol based on direction
    fn get_direction_symbol(&self, velocity: (f32, f32)) -> char {
        let abs_x = velocity.0.abs();
        let abs_y = velocity.1.abs();
    
        if abs_x > abs_y {
            // Horizontal movement (left or right)
            if velocity.0 > 0.0 {
                '⇒'  // Right
            } else {
                '⇐'  // Left
            }
        } else if abs_y > abs_x {
            // Vertical movement (up or down)
            if velocity.1 > 0.0 {
                '⇓'  // Down
            } else {
                '⇑'  // Up
            }
        } else {
            // Diagonal movement (approx. 45 degrees)
            if velocity.0 > 0.0 && velocity.1 < 0.0 {
                '⇗'  // Up-Right
            } else if velocity.0 < 0.0 && velocity.1 < 0.0 {
                '⇖'  // Up-Left
            } else if velocity.0 > 0.0 && velocity.1 > 0.0 {
                '⇘'  // Down-Right
            } else if velocity.0 < 0.0 && velocity.1 > 0.0 {
                '⇙'  // Down-Left
            } else {
                // If there is no movement, we can return a default symbol
                '•'  // Some placeholder for a boid with no movement
            }
        }
    }

    // Display the characters of the grid into the terminal
    fn display(&mut self, header: &str, boids: &[Boid], pois: &[POI], selected_poi_index: &usize) {

        // Move the cursor to the top of the terminal
        print!("\x1b[H"); 

        // Clear the old markings out of the grid
        for y in 0..self.rows {
            for x in 0..self.cols {
                self.data[y][x].0 = ' ';  // Clear out symbols.
                self.data[y][x].1 = String::new();  // Clear color.
            }
        }

        // Check if there are POIs
        if pois.is_empty() {
            println!("\r\x1B[2K{} | POI: 0/0 (+ Insert)", header);
        } else {
            // Get POI details for the header
            let total_pois = pois.len();
            
            // Ensure the selected POI index is valid
            if *selected_poi_index < total_pois {
                let selected_poi = &pois[*selected_poi_index];
                let poi_status = if selected_poi.toggled { "Attract" } else { "Repel" };
                println!("\r\x1B[2K{} - POI: (0..9 Select) {}/{} (+ Insert, - Delete) {} (Tab)", header, *selected_poi_index, total_pois - 1, poi_status);
            }
        }

        // Place Boids on grid
        for boid in boids {
            let x = boid.position.0.round() as usize;
            let y = boid.position.1.round() as usize;
    
            if 0 < x && x < self.cols && 0 < y && y < self.rows {
                // Mark Boid position with correct symbol
                self.data[y][x].0 = self.get_direction_symbol(boid.velocity); 
                self.data[y][x].1 = "\x1b[34m".to_string();
            }
        }

        // Place POIs on grid
        for (i, poi) in pois.iter().enumerate() {
            let x = poi.position.0 as usize;
            let y = poi.position.1 as usize;
    
            if 0 < x && x < self.cols && 0 < y && y < self.rows {
                if *selected_poi_index == i {
                    self.data[y][x].0 = '●'; // Selected POI
                } else {
                    self.data[y][x].0 = '○'; // Unselected POI
                }
    
                // Set color based on POI toggled status
                if poi.toggled {
                    self.data[y][x].1 = "\x1b[32m".to_string(); // Green for toggled POI
                } else {
                    self.data[y][x].1 = "\x1b[31m".to_string(); // Red for untoggled POI
                }
            }
        }
    
        // Display the grid characters with associated colors
        for y in 0..self.rows {
            let mut line = String::new();
            for x in 0..self.cols {
                let cell = &self.data[y][x];
                // Apply the color and then reset it for each cell in the grid
                line.push_str(&format!("{}{}\x1b[0m", cell.1, cell.0)); // Add color, symbol, then reset
            }
            println!("\r{}", line); // Output the line for the current row
            io::stdout().flush().unwrap();
        }
    }
}

struct POI {
    position: (f32, f32),
    toggled: bool,
}

impl POI {
    // Default to toggled on (attract)
    fn new(x: f32, y: f32) -> POI {
        POI {
            position: (x, y),
            toggled: true,
        }
    }

    // Toggle attract and repel
    fn toggle(&mut self) {
        self.toggled = !self.toggled;
    }

    // Move the poi with a given step
    fn step(&mut self, direction: (f32, f32)) {
        self.position.0 += direction.0;
        self.position.1 += direction.1;
    }
}

#[derive(Clone, PartialEq)]
struct Boid {
    position: (f32, f32),
    velocity: (f32, f32),
    view_range: f32,
    fov: f32,
    speed_limit: f32
}

impl Boid {
    fn new(x: f32, y: f32, vx: f32, vy: f32, vr: f32, fov: f32, spd: f32) -> Boid {
        Boid {
            position: (x, y),
            velocity: (vx, vy),
            view_range: vr,
            fov: fov,
            speed_limit: spd
        }
    }

    // Helper function to check if another boid should be considered
    fn within_view(&self, other_position: (f32, f32), distance_consideration: f32) -> bool {
        let diff_x = other_position.0 - self.position.0;
        let diff_y = other_position.1 - self.position.1;
        let distance = (diff_x.powi(2) + diff_y.powi(2)).sqrt();

        // Check if the other position is within the view range
        if distance > self.view_range {
            return false;
        }

        if distance > distance_consideration {
            return false;
        }

        // Normalize the difference vector
        let norm_x = diff_x / distance;
        let norm_y = diff_y / distance;

        // Get the normalized velocity vector
        let velocity_magnitude = (self.velocity.0.powi(2) + self.velocity.1.powi(2)).sqrt();
        let vel_x = self.velocity.0 / velocity_magnitude;
        let vel_y = self.velocity.1 / velocity_magnitude;

        // Compute the dot product
        let dot_product = norm_x * vel_x + norm_y * vel_y;

        // Compute the angle between the vectors
        let angle = dot_product.acos();

        // Check if the angle is within the FOV
        angle <= self.fov / 2.0
    }

    // To interact with POIs
    fn seek(&self, pois: &[POI]) -> (f32, f32) {
        let mut seek_force = (0.0, 0.0);

        for poi in pois {
            if self.within_view(poi.position, self.view_range * 4.0) {
                let diff_x = poi.position.0 - self.position.0;
                let diff_y = poi.position.1 - self.position.1;
                let distance = (diff_x.powi(2) + diff_y.powi(2)).sqrt();

                // Normalize the difference vector
                let norm_x = if distance != 0.0 { diff_x / distance } else { 0.0 };
                let norm_y = if distance != 0.0 { diff_y / distance } else { 0.0 };

                // Adjust force based on whether the POI is toggled
                if poi.toggled {
                    seek_force.0 += norm_x;
                    seek_force.1 += norm_y;
                } else {
                    seek_force.0 -= norm_x * 3.0;
                    seek_force.1 -= norm_y * 3.0;
                }
            }
        }

        seek_force
    }

    // Move away from boids in range
    fn separation(&self, boids: &[Boid]) -> (f32, f32) {
        let mut steer = (0.0, 0.0);
        let mut count = 0;

        for other in boids {
            if other != self && self.within_view(other.position, self.view_range * 0.5) {
                let diff = (
                    self.position.0 - other.position.0,
                    self.position.1 - other.position.1,
                );
                let dist = (diff.0.powi(2) + diff.1.powi(2)).sqrt();
                let magnitude = (dist.max(1.0)).powi(2);
                steer.0 += diff.0 / magnitude;
                steer.1 += diff.1 / magnitude;
                count += 1;
            }
        }

        if count > 0 {
            steer.0 /= count as f32;
            steer.1 /= count as f32;
        }

        let length = (steer.0.powi(2) + steer.1.powi(2)).sqrt();
        if length > 0.0 {
            steer.0 /= length;
            steer.1 /= length;
        }

        steer
    }

    // Match direction of boids in range
    fn alignment(&self, boids: &[Boid]) -> (f32, f32) {
        let mut sum_velocity = (0.0, 0.0);
        let mut count = 0;

        for other in boids {
            if other != self && self.within_view(other.position, self.view_range * 0.65) {
                sum_velocity.0 += other.velocity.0;
                sum_velocity.1 += other.velocity.1;
                count += 1;
            }
        }

        if count > 0 {
            sum_velocity.0 /= count as f32;
            sum_velocity.1 /= count as f32;
        }

        let length = (sum_velocity.0.powi(2) + sum_velocity.1.powi(2)).sqrt();
        if length > 0.0 {
            sum_velocity.0 /= length;
            sum_velocity.1 /= length;
        }

        sum_velocity
    }

    // Tend towards boid in range
    fn cohesion(&self, boids: &[Boid]) -> (f32, f32) {
        let mut center_of_mass = (0.0, 0.0);
        let mut count = 0;

        for other in boids {
            if other != self && self.within_view(other.position, self.view_range) {
                center_of_mass.0 += other.position.0;
                center_of_mass.1 += other.position.1;
                count += 1;
            }
        }

        if count > 0 {
            center_of_mass.0 /= count as f32;
            center_of_mass.1 /= count as f32;

            let mut diff = (center_of_mass.0 - self.position.0, center_of_mass.1 - self.position.1);
            let length = (diff.0.powi(2) + diff.1.powi(2)).sqrt();
            if length > 0.0 {
                diff.0 /= length;
                diff.1 /= length;
            }

            return diff;
        }

        (0.0, 0.0)
    }

    // Apply behaviors to boid
    fn update(&mut self, boids: &[Boid], pois: &[POI], space_width: f32, space_height: f32) {
        let separation_force = self.separation(boids);
        let alignment_force = self.alignment(boids);
        let cohesion_force = self.cohesion(boids);
        let seek_force = self.seek(pois);

        let mut desired_velocity_x = separation_force.0 * 1.5
            + alignment_force.0
            + cohesion_force.0 * 1.25
            + seek_force.0 * 1.75;
        let mut desired_velocity_y = separation_force.1 * 1.5
            + alignment_force.1
            + cohesion_force.1 * 1.25
            + seek_force.1 * 1.75;
        


        let desired_speed = (desired_velocity_x.powi(2) + desired_velocity_y.powi(2)).sqrt();
        if desired_speed > self.speed_limit {
            let d_scale = self.speed_limit / desired_speed;
            desired_velocity_x *= d_scale;
            desired_velocity_y *= d_scale;
        }

        self.velocity.0 += 0.1 * (desired_velocity_x - self.velocity.0);
        self.velocity.1 += 0.1 * (desired_velocity_y - self.velocity.1);

        // Enforce the speed limit
        let speed = (self.velocity.0.powi(2) + self.velocity.1.powi(2)).sqrt();
        if speed > self.speed_limit {
            let scale = self.speed_limit / speed;
            self.velocity.0 *= scale;
            self.velocity.1 *= scale;
        }

        // Prevent the boid from getting stuck if speed is too low
        if speed <= 0.25 {
            self.velocity.0 += 0.25;
            self.velocity.1 += 0.25;
        }

        self.position.0 += self.velocity.0;
        self.position.1 += self.velocity.1;

        if self.position.0 <= 0.0 {
            self.position.0 = 0.0;
            self.velocity.0 = -self.velocity.0;
        } else if self.position.0 >= space_width {
            self.position.0 = space_width;
            self.velocity.0 = -self.velocity.0;
        }
    
        if self.position.1 <= 0.0 {
            self.position.1 = 0.0;
            self.velocity.1 = -self.velocity.1;
        } else if self.position.1 >= space_height {
            self.position.1 = space_height;
            self.velocity.1 = -self.velocity.1;
        }
    }
}


fn main() -> Result<(), Box<dyn Error>> {
    // Prep terminal for grid display method
    let mut stdout = io::stdout();
    terminal::enable_raw_mode().unwrap();
    stdout.execute(terminal::Clear(terminal::ClearType::All))?;
    stdout.execute(cursor::Hide)?;

    // Get the size of the terminal 
    let (mut cols, mut rows) = terminal::size().unwrap();
    // Put a buffer on the edge
    rows = (rows as f32 * 0.95).floor() as u16;
    cols = (cols as f32 * 0.95).floor() as u16;
    let mut grid = Grid::new(rows.into(), cols.into());

    // Make lists for POIs and boids
    let mut pois: Vec<POI> = Vec::new();
    let mut boids: Vec<Boid> = Vec::new();

    // Get a start time for elapsed calculation
    let start_time = Instant::now();
    // Set a limit for how fast a frame can pass
    let target_duration = Duration::from_millis(33);

    // Start with a default poi index
    let mut selected_poi_index = 0;

    loop {
        // get start of loop time for frame duration calculation
        let loop_start = Instant::now();

        // Poll for user key inputs
        if event::poll(Duration::from_millis(10))? {
            if let event::Event::Key(KeyEvent { code, .. }) = event::read()? {
                match code {
                    // Directional keys
                    KeyCode::Left | KeyCode::Right | KeyCode::Up | KeyCode::Down => {
                        if let Some(poi) = pois.get_mut(selected_poi_index) {
                            let (dx, dy) = match code {
                                KeyCode::Left => (-1.0, 0.0),
                                KeyCode::Right => (1.0, 0.0),
                                KeyCode::Up => (0.0, -1.0),
                                KeyCode::Down => (0.0, 1.0),
                                _ => (0.0, 0.0),
                            };
                
                            let new_x = poi.position.0 + dx;
                            let new_y = poi.position.1 + dy;
                
                            // Ensure boundaries
                            if new_x >= 0.0 && new_x < cols as f32 && new_y >= 0.0 && new_y < rows as f32 {
                                poi.step((dx, dy));
                            }
                        }
                    }
                
                    // Tab to toggle
                    KeyCode::Tab => {
                        if let Some(poi) = pois.get_mut(selected_poi_index) {
                            poi.toggle();
                        }
                    }
                
                    // Insert to add a POI
                    KeyCode::Insert => {
                        if pois.len() < 10 {
                            let center_x = (cols as f32 / 2.0).floor();
                            let center_y = (rows as f32 / 2.0).floor();
                            let new_poi = POI::new(center_x, center_y);
                
                            pois.push(new_poi);
                            selected_poi_index = pois.len() - 1;
                        }
                    }
                
                    // Delete to remove a POI
                    KeyCode::Delete => {
                        if !pois.is_empty() {
                            pois.remove(selected_poi_index);
                            selected_poi_index = selected_poi_index.min(pois.len().saturating_sub(1));
                        }
                    }
                
                    // Number keys to select POIs
                    KeyCode::Char(c) if c.is_digit(10) => {
                        let index = c.to_digit(10).unwrap() as usize;
                        if index < pois.len() {
                            selected_poi_index = index;
                        }
                    }
                
                    // Enter to add a Boid
                    KeyCode::Enter => {
                        boids.push(Boid::new(
                            rand::thread_rng().gen_range(0.0..cols as f32),
                            rand::thread_rng().gen_range(0.0..rows as f32),
                            rand::thread_rng().gen_range(-10.0..10.0),
                            rand::thread_rng().gen_range(-10.0..10.0),
                            5.0,
                            25.0,
                            1.5,
                        ));
                    }
                
                    // Backspace to remove a Boid
                    KeyCode::Backspace => {
                        boids.pop();
                    }
                
                    // Escape to exit
                    KeyCode::Esc => {
                        println!("\r");
                        terminal::disable_raw_mode().unwrap();
                        stdout.execute(cursor::Show)?;
                        break Ok(());
                    }
                
                    _ => {}
                }
            }
        }

        // Make the timestamp header
        let elapsed = start_time.elapsed();
        let secs = elapsed.as_secs_f32();
        let time_str = format!("Time: {:.1}s (Esc)", secs);
        let boid_count_str = format!("Boids: {} (+ Enter, - Backspace)", boids.len());
        let header = format!("{} | {}", time_str, boid_count_str);

        // Use a copy of boids for a frozen boid state
        let old_boids = boids.clone();
        // Update each boid referencing frozen boid state
        for boid in &mut boids {
            boid.update(&old_boids, &pois, cols as f32, rows as f32)
        }

        // Re-display the grid to the terminal with all important info
        grid.display(&header, &boids, &pois, &selected_poi_index);

        // Get current frame duration
        let iteration_duration = loop_start.elapsed();

        // If the iteration was too fast, sleep for the remaining time
        if iteration_duration < target_duration {
            sleep(target_duration - iteration_duration);
        }
    }
}


