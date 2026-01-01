# update_cat_ids.py
# Update all existing cat IDs to CAT133001239 format
# Run: python manage.py shell < update_cat_ids.py

from task_management.models import Cat

print("=" * 80)
print("UPDATING CAT IDs TO CAT133001239 FORMAT")
print("=" * 80)

cats = Cat.objects.all().order_by('id')
total = cats.count()

if total == 0:
    print("\n✅ No cats in database to update!")
    print("=" * 80)
else:
    print(f"\nFound {total} cat(s) to update")
    
    # Ask for confirmation (comment out in production)
    # response = input("\nProceed with update? (yes/no): ")
    # if response.lower() != 'yes':
    #     print("❌ Update cancelled")
    #     exit()
    
    print("\nUpdating...")
    print("-" * 80)
    
    updated = 0
    errors = 0
    
    for index, cat in enumerate(cats, 1):
        old_id = cat.cat_id
        
        try:
            # Force regenerate cat_id
            cat.cat_id = None
            cat.cat_id = cat.generate_cat_id()
            cat.save()
            
            print(f"{index}/{total} - ✅ {old_id} → {cat.cat_id} ({cat.name})")
            updated += 1
            
        except Exception as e:
            print(f"{index}/{total} - ❌ ERROR: {old_id} - {str(e)}")
            errors += 1
    
    print("-" * 80)
    print(f"\n📊 SUMMARY:")
    print(f"Total cats: {total}")
    print(f"Successfully updated: {updated} ✅")
    print(f"Errors: {errors} ❌")
    print("=" * 80)
    
    if errors == 0:
        print("\n🎉 ALL CAT IDs UPDATED SUCCESSFULLY!")
        print("\nNew format examples:")
        
        # Show some examples
        sample_cats = Cat.objects.all()[:5]
        for cat in sample_cats:
            print(f"  {cat.cat_id} - {cat.name}")
    else:
        print(f"\n⚠️  {errors} error(s) occurred.")
        print("Please check the errors above and try again.")
    
    print("\n" + "=" * 80)