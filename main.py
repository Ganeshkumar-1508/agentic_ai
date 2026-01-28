from crew import crew
from cache.cache_manager import get_from_cache, store_in_cache,delete_from_cache   
import time


def main():
    print("=== CrewAI Report Generator (Cache First) ===")

    while True:
        topic = input("\nEnter report topic (or 'q' /'quit' to exit): ").strip()

        if topic.lower() in ("q", "quit"):
            print("Exiting the application. Goodbye..")
            break

        start_time = time.time()

        #  Check cache first
        cached_answer = get_from_cache(topic)

        #  If cache found
        if cached_answer:
            print("\nFinal Report (From Cache)\n")
            print(cached_answer)

            refresh = input("\nDo you want latest data? (T/F): ").strip().lower()
                
            if refresh != "t":
                print("\n Using cached data")
                continue

            # User wants latest
            print("\n Fetching latest information...")
            latest_information = crew.kickoff(inputs={"topic": topic})
                

            # Replace cache
            delete_from_cache(topic)
            store_in_cache(topic, str(latest_information))

            print("\n Final Report (Latest)\n")
            print(latest_information)
            continue

        #  Cache not found  go to web
        print("\n No cache found. Fetching from web...")
        result = crew.kickoff(inputs={"topic": topic})
 
        store_in_cache(topic, str(result))

        print("\n Final Report\n")
        print(result)

        end_time = time.time()
        print(f"\nExecution time: {end_time - start_time:.2f} seconds")


if __name__ == "__main__":
    main()
