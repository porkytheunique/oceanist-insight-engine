def analyze_coral_proximity(platform_data, coral_data):
    """
    Finds a random oil/gas platform that is close to a coral reef.
    """
    print("\n--- Starting Story Analysis: Coral Proximity ---")
    platform_features = platform_data.get('features', [])
    coral_features = coral_data.get('features', [])

    if not platform_features or not coral_features:
        print("  - ❌ Cannot run analysis: Missing platform or coral data.")
        return None

    print(f"  - Pre-processing {len(coral_features)} coral reef geometries...")
    coral_shapes = [shape(geom['geometry']) for geom in coral_features if geom.get('geometry')]
    print(f"  - Successfully processed {len(coral_shapes)} valid coral reef shapes.")

    print("  - 🗺️ Building spatial index for all coral reefs...")
    idx = index.Index()
    valid_shapes_for_index = []
    for i, coral_shape in enumerate(coral_shapes):
        # --- NEW VALIDATION STEP ---
        # A valid bounding box has min_x <= max_x and min_y <= max_y
        min_x, min_y, max_x, max_y = coral_shape.bounds
        if min_x <= max_x and min_y <= max_y:
            idx.insert(i, coral_shape.bounds)
            valid_shapes_for_index.append(coral_shape)
        # ---------------------------
        
    print(f"  - ✅ Spatial index built successfully with {len(valid_shapes_for_index)} valid shapes.")
        
    platform = random.choice(platform_features)
    platform_point = shape(platform['geometry'])
    
    print(f"  - Analyzing a random platform: '{platform['properties'].get('Unit Name', 'Unnamed')}'")

    nearest_coral_indices = list(idx.nearest(platform_point.bounds, 5))
    
    min_distance = float('inf')
    closest_coral_feature = None

    for coral_idx in nearest_coral_indices:
        # Use the validated list of shapes
        distance = platform_point.distance(valid_shapes_for_index[coral_idx])
        if distance < min_distance:
            min_distance = distance
            # Find the original feature data that corresponds to this shape
            closest_coral_feature = coral_features[coral_idx]

    if closest_coral_feature:
        story_data = {
            "story_type": "coral_proximity",
            "platform_name": platform['properties'].get('Unit Name', 'Unnamed Platform'),
            "platform_country": platform['properties'].get('Country/Area', 'an unknown location'),
            "platform_coords": platform['geometry']['coordinates'],
            "coral_ecoregion": closest_coral_feature['properties'].get('ECOREGION', 'a sensitive marine area'),
            "distance_km": min_distance * 111.32
        }
        print("  ✅ Analysis Complete: Found a notable proximity event.")
        print(f"     - Platform '{story_data['platform_name']}' is {story_data['distance_km']:.2f} km from a coral reef in the '{story_data['coral_ecoregion']}' ecoregion.")
        return story_data
    else:
        print("  - ❌ Analysis Complete: Could not find a nearby coral reef for the selected platform.")
        return None
