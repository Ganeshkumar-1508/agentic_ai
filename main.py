from crew import crew
import time

def generate_report(topic: str):
    return crew.kickoff(inputs={"topic": topic})

def main():
    print("=== CrewAI Report Generator (NVIDIA Cloud) ===")
    while True:
        topic = input("\nEnter report topic(or 'q' / 'quit' to exit): ").strip()

        if topic.lower() in ('q',"quit"):
            print("Exiting the application . Goodbye")
            break

        start_time=time.time()
        
        #result = crew.kickoff(inputs={"topic": topic})
        result = generate_report(topic)

        end_time=time.time()
        
        print("\nFINAL REPORT\n")
        print(result)

        time_taken=(end_time - start_time)
        print("\n Execution time \n")
        print(f"The time taken:{time_taken:.2f}seconds")

if __name__ == "__main__":
    main()
