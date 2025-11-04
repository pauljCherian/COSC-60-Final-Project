# CS 60 | Computer Networks | Fall 2025
Project \[20 points\]
---------------------

Toward the end of the term you will work on a network-related project of your choosing with another student. This project can be as extensive as you'd like, but remember you'll only have one term to work on it. I will meet with each team individually during week seven to discuss your project. In the end you will present/demo an overview of your project to the class.

Projects should be reasonably substantial. Simple projects may not receive full credit. I will clarify after our initial team meeting if the project seems to simple (or too complex).

An example of a reasonable project is to implement reliable data transfer between hosts using UDP instead of TCP. UDP does not inherently do not guarantee delivery, ordering, or error checking. The goal is to simulate TCP-like reliability features over UDP.

Implement:

1.  Packet Sequencing: Add sequence numbers to packets to ensure correct ordering
2.  Acknowledgments (ACKs): Implement ACKs for received packets. Optionally, use cumulative ACKs or selective ACKs
3.  Timeouts and Retransmissions: Use timers to detect lost packets and trigger retransmissions
4.  Sliding Window Protocol: Implement a basic version of Go-Back-N or Selective Repeat for efficiency
5.  Checksum/Error Detection: Add a checksum to detect corrupted packets
6.  Congestion Control (Optional Advanced Feature): Simulate basic congestion control mechanisms like TCP’s slow start.

Another example project is to implement this [zombie tag game](https://www.youtube.com/watch?v=TjCUs_oYcsY). I have a small number of ESP32 devices (the video uses the older ESP8266 but the ESP32 is more capable) that you can borrow. While we won't have the LED strip like the game in the video, you can blink the built-in LED to achieve a similar effect.

### Team composition

You will work in teams of two students. You can request a specific partner for the final project, see the assignment page on Canvas. If you do not sign up for a partner by Oct 22, I will assign you a random partner on Oct 23. Each student on a team will receive the same grade for the project.

### Evaluation

The final project is worth 20% of the final grade and consists of several phases:

*   **\[3 points\] Requirements specification.** Write a 1-3 page description of your project, what is does, who is serves, the major entities involved, the business rules required, and a plan for the network communications. We will discuss this in person as indicated on the [Schedule page](./schedule.html) of the course web site. You should view this in-person meeting as if you were trying to convince a manager at a company to fund your idea. Document your project as described in CS50 (see [Requirements.md](https://www.cs.dartmouth.edu/~tjp/cs50/notes/notes17#requirements-spec) and [slides](https://www.cs.dartmouth.edu/~tjp/cs50/slides/Day17.pdf)). Submit a pdf of your write up, listing each team member, on Canvas.
  
*   **\[3 points\] Implementation specification.** Describe how you will implement your project as described in CS50 (see [Implementation.md](https://www.cs.dartmouth.edu/~tjp/cs50/notes/notes17#implementation-spec)). Submit a pdf of your write up, listing each team member, on Canvas.
  
*   **\[9 points\] Code implementation:**  
    *   2%: Good coding practices (code organization, variable names, etc)
    *   2%: Evidence of testing
    *   5%: Functionality (code works as described in requirements and implementation documents)
  
*   **\[5 points\] Final presentation.** Each team will record a 10 minute video presentation/demo their project where you will give an overview of your project and highlight how you solved it. Submit a final pdf write up of your project updating your original project plan. Highlight the changes from your initial plan as you implemented your final solution. Submit this video on Canvas.
**Project presentation rubric:**

*   2%: Presentation quality

*   Clear description of project
*   Presented in logical order
*   Easy to understand design and implementation choices

*   2%: Demo of implemented features
*   1%: Discussion of challenges/changes from initial plan.