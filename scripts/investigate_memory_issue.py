"""
Investigation script to analyze broken memory issues
Examines chats with oversized memories and detects repetition patterns
"""
import re
from collections import Counter
from app.db.base import get_db
from app.db import crud
from app.db.models import Chat


def detect_repetition(text: str) -> dict:
    """
    Analyze text for repetition patterns
    
    Returns dict with:
    - repetition_score: 0-100 (higher = more repetitive)
    - repeated_phrases: list of phrases that repeat
    - unique_ratio: ratio of unique sentences to total
    """
    if not text:
        return {"repetition_score": 0, "repeated_phrases": [], "unique_ratio": 1.0}
    
    # Split into sentences
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    if not sentences:
        return {"repetition_score": 0, "repeated_phrases": [], "unique_ratio": 1.0}
    
    # Count sentence occurrences
    sentence_counts = Counter(sentences)
    
    # Find repeated sentences (appearing 2+ times)
    repeated = [(sent, count) for sent, count in sentence_counts.items() if count > 1]
    repeated.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate unique ratio
    unique_sentences = len(sentence_counts)
    total_sentences = len(sentences)
    unique_ratio = unique_sentences / total_sentences if total_sentences > 0 else 1.0
    
    # Calculate repetition score (0-100)
    # Lower unique ratio = higher repetition score
    repetition_score = int((1 - unique_ratio) * 100)
    
    return {
        "repetition_score": repetition_score,
        "repeated_phrases": repeated[:5],  # Top 5 repeated
        "unique_ratio": unique_ratio,
        "total_sentences": total_sentences,
        "unique_sentences": unique_sentences
    }


def analyze_memory(memory: str, chat_id: str) -> None:
    """Print detailed analysis of a single memory"""
    print(f"\n{'='*80}")
    print(f"Chat ID: {chat_id}")
    print(f"Memory Length: {len(memory)} characters")
    print(f"{'='*80}")
    
    # Detect repetition
    rep_info = detect_repetition(memory)
    
    print(f"\n📊 Repetition Analysis:")
    print(f"   Repetition Score: {rep_info['repetition_score']}/100")
    print(f"   Unique Ratio: {rep_info['unique_ratio']:.2%} ({rep_info['unique_sentences']}/{rep_info['total_sentences']} unique)")
    
    if rep_info['repeated_phrases']:
        print(f"\n🔄 Top Repeated Phrases:")
        for phrase, count in rep_info['repeated_phrases']:
            print(f"   [{count}x] {phrase[:80]}{'...' if len(phrase) > 80 else ''}")
    
    # Show preview of memory
    print(f"\n📝 Memory Preview (first 500 chars):")
    print(f"   {memory[:500]}...")
    
    # Show end of memory
    if len(memory) > 1000:
        print(f"\n📝 Memory End (last 300 chars):")
        print(f"   ...{memory[-300:]}")


def main():
    """Main investigation function"""
    print("🔍 Investigating Memory Issues")
    print("="*80)
    
    with get_db() as db:
        # Get all chats
        all_chats = db.query(Chat).all()
        
        # Filter chats with memory > 1000 chars
        oversized_chats = [
            chat for chat in all_chats 
            if chat.memory and len(chat.memory) > 1000
        ]
        
        print(f"\n📈 Statistics:")
        print(f"   Total chats: {len(all_chats)}")
        print(f"   Chats with memory > 1000 chars: {len(oversized_chats)}")
        
        if not oversized_chats:
            print("\n✅ No oversized memories found!")
            return
        
        # Analyze each oversized memory
        print(f"\n{'='*80}")
        print("DETAILED ANALYSIS OF OVERSIZED MEMORIES")
        print(f"{'='*80}")
        
        for chat in oversized_chats:
            analyze_memory(chat.memory, str(chat.id))
        
        # Summary statistics
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        
        total_rep_score = 0
        high_repetition_count = 0
        
        for chat in oversized_chats:
            rep_info = detect_repetition(chat.memory)
            total_rep_score += rep_info['repetition_score']
            if rep_info['repetition_score'] > 50:
                high_repetition_count += 1
        
        if oversized_chats:
            avg_rep_score = total_rep_score / len(oversized_chats)
            print(f"   Average Repetition Score: {avg_rep_score:.1f}/100")
            print(f"   High Repetition (>50): {high_repetition_count}/{len(oversized_chats)}")
        
        # Show size distribution
        sizes = [len(chat.memory) for chat in oversized_chats]
        print(f"\n   Size Distribution:")
        print(f"      Min: {min(sizes)} chars")
        print(f"      Max: {max(sizes)} chars")
        print(f"      Avg: {sum(sizes)/len(sizes):.0f} chars")


if __name__ == "__main__":
    main()

