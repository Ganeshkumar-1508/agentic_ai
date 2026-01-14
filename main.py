from crew import crew

def main():
    print("=== CrewAI Report Generator (NVIDIA Cloud) ===")
    topic = input("Enter report topic: ")

    result = crew.kickoff(inputs={"topic": topic})

    print("\nFINAL REPORT\n")
    print(result)

if __name__ == "__main__":
    main()
