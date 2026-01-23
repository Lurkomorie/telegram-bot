"""
Script to find duplicate image prompts in the database.
Uses batch processing to avoid overwhelming the database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db.models import Persona, PersonaHistoryStart, ImageJob


def find_duplicate_persona_prompts(session: Session, batch_size: int = 100):
    """Find duplicate image_prompt values in Persona table"""
    print("\n=== Checking Persona image_prompt duplicates ===")
    
    # Get total count
    total = session.query(func.count(Persona.id)).filter(Persona.image_prompt.isnot(None)).scalar()
    print(f"Total personas with image_prompt: {total}")
    
    # Process in batches
    prompt_to_personas = defaultdict(list)
    offset = 0
    
    while offset < total:
        batch = session.query(
            Persona.id, Persona.key, Persona.name, Persona.image_prompt
        ).filter(
            Persona.image_prompt.isnot(None)
        ).limit(batch_size).offset(offset).all()
        
        for persona_id, key, name, image_prompt in batch:
            # Normalize prompt (strip whitespace for comparison)
            normalized_prompt = image_prompt.strip() if image_prompt else ""
            if normalized_prompt:
                prompt_to_personas[normalized_prompt].append({
                    'id': str(persona_id),
                    'key': key,
                    'name': name
                })
        
        offset += batch_size
        print(f"Processed {min(offset, total)}/{total} personas...")
    
    # Find duplicates
    duplicates = {prompt: personas for prompt, personas in prompt_to_personas.items() if len(personas) > 1}
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate image prompts in Persona table:")
        for i, (prompt, personas) in enumerate(duplicates.items(), 1):
            print(f"\n{i}. Duplicate prompt (used by {len(personas)} personas):")
            print(f"   Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"   Prompt: {prompt}")
            print(f"   Used by:")
            for p in personas:
                print(f"     - {p['name']} (key: {p['key']}, id: {p['id']})")
    else:
        print("\nNo duplicate image prompts found in Persona table.")
    
    return duplicates


def find_duplicate_history_prompts(session: Session, batch_size: int = 100):
    """Find duplicate image_prompt values in PersonaHistoryStart table"""
    print("\n=== Checking PersonaHistoryStart image_prompt duplicates ===")
    
    # Get total count
    total = session.query(func.count(PersonaHistoryStart.id)).filter(
        PersonaHistoryStart.image_prompt.isnot(None)
    ).scalar()
    print(f"Total history starts with image_prompt: {total}")
    
    # Process in batches
    prompt_to_histories = defaultdict(list)
    offset = 0
    
    while offset < total:
        batch = session.query(
            PersonaHistoryStart.id,
            PersonaHistoryStart.name,
            PersonaHistoryStart.persona_id,
            PersonaHistoryStart.image_prompt
        ).filter(
            PersonaHistoryStart.image_prompt.isnot(None)
        ).limit(batch_size).offset(offset).all()
        
        for history_id, name, persona_id, image_prompt in batch:
            # Normalize prompt (strip whitespace for comparison)
            normalized_prompt = image_prompt.strip() if image_prompt else ""
            if normalized_prompt:
                prompt_to_histories[normalized_prompt].append({
                    'id': str(history_id),
                    'name': name,
                    'persona_id': str(persona_id)
                })
        
        offset += batch_size
        print(f"Processed {min(offset, total)}/{total} history starts...")
    
    # Find duplicates
    duplicates = {prompt: histories for prompt, histories in prompt_to_histories.items() if len(histories) > 1}
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate image prompts in PersonaHistoryStart table:")
        for i, (prompt, histories) in enumerate(duplicates.items(), 1):
            print(f"\n{i}. Duplicate prompt (used by {len(histories)} history starts):")
            print(f"   Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"   Prompt: {prompt}")
            print(f"   Used by:")
            for h in histories:
                print(f"     - {h['name']} (persona_id: {h['persona_id']}, id: {h['id']})")
    else:
        print("\nNo duplicate image prompts found in PersonaHistoryStart table.")
    
    return duplicates


def find_duplicate_image_job_prompts(session: Session, batch_size: int = 500):
    """Find duplicate prompt values in ImageJob table"""
    print("\n=== Checking ImageJob prompt duplicates ===")
    
    # Get total count
    total = session.query(func.count(ImageJob.id)).filter(ImageJob.prompt.isnot(None)).scalar()
    print(f"Total image jobs with prompt: {total}")
    
    if total > 10000:
        print(f"⚠️  Warning: Large dataset ({total} records). This may take a while...")
    
    # Process in batches
    prompt_to_jobs = defaultdict(list)
    offset = 0
    
    while offset < total:
        batch = session.query(
            ImageJob.id,
            ImageJob.prompt,
            ImageJob.status,
            ImageJob.created_at
        ).filter(
            ImageJob.prompt.isnot(None)
        ).limit(batch_size).offset(offset).all()
        
        for job_id, prompt, status, created_at in batch:
            # Normalize prompt (strip whitespace for comparison)
            normalized_prompt = prompt.strip() if prompt else ""
            if normalized_prompt:
                prompt_to_jobs[normalized_prompt].append({
                    'id': str(job_id),
                    'status': status,
                    'created_at': created_at.isoformat() if created_at else None
                })
        
        offset += batch_size
        print(f"Processed {min(offset, total)}/{total} image jobs...")
    
    # Find duplicates
    duplicates = {prompt: jobs for prompt, jobs in prompt_to_jobs.items() if len(jobs) > 1}
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate prompts in ImageJob table:")
        # Show top 10 most duplicated prompts
        sorted_duplicates = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
        
        print(f"\nTop 10 most duplicated prompts:")
        for i, (prompt, jobs) in enumerate(sorted_duplicates[:10], 1):
            print(f"\n{i}. Duplicate prompt (used {len(jobs)} times):")
            print(f"   Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"   Prompt: {prompt}")
            print(f"   Status breakdown:")
            status_counts = defaultdict(int)
            for job in jobs:
                status_counts[job['status']] += 1
            for status, count in status_counts.items():
                print(f"     - {status}: {count}")
        
        if len(duplicates) > 10:
            print(f"\n... and {len(duplicates) - 10} more duplicate prompts")
    else:
        print("\nNo duplicate prompts found in ImageJob table.")
    
    return duplicates


def generate_summary_report(persona_dupes, history_dupes, job_dupes):
    """Generate a summary report of all duplicates"""
    print("\n" + "="*60)
    print("SUMMARY REPORT")
    print("="*60)
    
    print(f"\nPersona table:")
    print(f"  - Unique prompts with duplicates: {len(persona_dupes)}")
    if persona_dupes:
        total_duplicate_personas = sum(len(personas) for personas in persona_dupes.values())
        print(f"  - Total personas affected: {total_duplicate_personas}")
    
    print(f"\nPersonaHistoryStart table:")
    print(f"  - Unique prompts with duplicates: {len(history_dupes)}")
    if history_dupes:
        total_duplicate_histories = sum(len(histories) for histories in history_dupes.values())
        print(f"  - Total history starts affected: {total_duplicate_histories}")
    
    print(f"\nImageJob table:")
    print(f"  - Unique prompts with duplicates: {len(job_dupes)}")
    if job_dupes:
        total_duplicate_jobs = sum(len(jobs) for jobs in job_dupes.values())
        print(f"  - Total image jobs affected: {total_duplicate_jobs}")
        
        # Calculate potential savings
        potential_savings = total_duplicate_jobs - len(job_dupes)
        print(f"  - Potential duplicate generations: {potential_savings}")
    
    print("\n" + "="*60)


def main():
    """Main function to check all tables for duplicate image prompts"""
    print("Starting duplicate image prompt analysis...")
    print("This script uses batch processing to avoid overwhelming the database.\n")
    
    with get_db() as session:
        try:
            # Check each table
            persona_dupes = find_duplicate_persona_prompts(session, batch_size=100)
            history_dupes = find_duplicate_history_prompts(session, batch_size=100)
            job_dupes = find_duplicate_image_job_prompts(session, batch_size=500)
            
            # Generate summary
            generate_summary_report(persona_dupes, history_dupes, job_dupes)
            
        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
