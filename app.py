"""
Flask web server for Corall paper recommendation system.
"""
import os
import json
import signal
import webbrowser
import threading
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

from src.recommender import PaperRecommender
from src.journal_lists import TOP_BIOLOGY_MEDICINE_JOURNALS, load_journals_from_file
from src.reviewed_papers import ReviewedPapersManager
from src.email_sender import EmailSender
from src.config_manager import ConfigManager

load_dotenv()

app = Flask(__name__)
CORS(app)

# Global config manager
config_manager = ConfigManager()

# Global recommender instance
recommender = None
is_initialized = False

# Global reviewed papers manager
reviewed_manager = ReviewedPapersManager()

# Global email sender
email_sender = EmailSender()


@app.route('/')
def index():
    """Serve the main HTML page."""
    # Check if setup is completed
    if not config_manager.is_setup_completed():
        return redirect(url_for('setup'))
    return render_template('index.html')


@app.route('/setup')
def setup():
    """Serve the setup page."""
    return render_template('setup.html')


@app.route('/reviewed')
def reviewed_page():
    """Serve the reviewed papers page."""
    return render_template('reviewed.html')


@app.route('/api/setup/test-zotero', methods=['POST'])
def test_zotero():
    """Test Zotero connection."""
    try:
        data = request.json or {}
        api_key = data.get('api_key')
        user_id = data.get('user_id')
        library_type = data.get('library_type', 'user')

        if not api_key or not user_id:
            return jsonify({
                'success': False,
                'message': 'API key and User ID are required'
            }), 400

        # Temporarily set environment variables for testing
        os.environ['ZOTERO_API_KEY'] = api_key
        os.environ['ZOTERO_USER_ID'] = user_id
        os.environ['ZOTERO_LIBRARY_TYPE'] = library_type

        # Test connection
        from src.zotero_client import ZoteroClient
        client = ZoteroClient()
        collections = client.list_collections()

        return jsonify({
            'success': True,
            'message': f'Successfully connected! Found {len(collections)} collections.',
            'collections': collections
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Connection failed: {str(e)}'
        }), 500


@app.route('/api/setup/list-collections', methods=['POST'])
def list_collections():
    """List Zotero collections."""
    try:
        data = request.json or {}
        api_key = data.get('api_key')
        user_id = data.get('user_id')
        library_type = data.get('library_type', 'user')

        if not api_key or not user_id:
            return jsonify({
                'success': False,
                'error': 'API key and User ID are required'
            }), 400

        # Temporarily set environment variables
        os.environ['ZOTERO_API_KEY'] = api_key
        os.environ['ZOTERO_USER_ID'] = user_id
        os.environ['ZOTERO_LIBRARY_TYPE'] = library_type

        from src.zotero_client import ZoteroClient
        client = ZoteroClient()
        collections = client.list_collections()

        return jsonify({
            'success': True,
            'collections': collections
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/setup/initialize', methods=['POST'])
def setup_initialize():
    """Complete setup and initialize the system."""
    global recommender, is_initialized

    try:
        data = request.json or {}

        # Update config manager with new configuration
        config_manager.config['zotero'] = data.get('zotero', {})
        config_manager.config['openalex'] = data.get('openalex', {})
        config_manager.config['recommendation'] = data.get('recommendation', {})

        # Validate configuration
        is_valid, error_msg = config_manager.validate_zotero_config()
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        # Update .env file
        config_manager.update_env_file()

        # Reload environment variables
        load_dotenv(override=True)

        # Set collection ID if provided
        collection_id = config_manager.config['zotero'].get('collection_id')
        if collection_id:
            os.environ['ZOTERO_COLLECTION_ID'] = collection_id

        # Initialize recommender
        recommender = PaperRecommender()
        recommender.initialize(force_rebuild=False)
        is_initialized = True

        # Mark setup as completed
        config_manager.mark_setup_completed()
        config_manager.save_config()

        return jsonify({
            'success': True,
            'message': 'Setup completed and system initialized successfully'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration."""
    rec_config = config_manager.get_recommendation_config()
    return jsonify({
        'citation_weight': rec_config.get('citation_weight', 0.3),
        'similarity_weight': rec_config.get('similarity_weight', 0.7),
        'default_days_back': rec_config.get('default_days_back', 30),
        'default_top_n': rec_config.get('default_top_n', 100)
    })


@app.route('/api/setup/config', methods=['GET'])
def get_setup_config():
    """Get full configuration for setup page."""
    return jsonify({
        'setup_completed': config_manager.is_setup_completed(),
        'zotero': config_manager.get_zotero_config(),
        'openalex': config_manager.config.get('openalex', {}),
        'recommendation': config_manager.get_recommendation_config()
    })


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get initialization status."""
    cache_dir = ".cache"
    # Allow checking status for a specific collection via query param
    collection_id = request.args.get('collection_id') or os.getenv('ZOTERO_COLLECTION_ID') or 'all'
    collection_key = (''.join(c if c.isalnum() else '_' for c in collection_id.lower()).strip('_') or 'all')
    embeddings_exist = os.path.exists(os.path.join(cache_dir, f"library_embeddings_{collection_key}.pkl"))
    citation_exist = os.path.exists(os.path.join(cache_dir, f"citation_network_{collection_key}.pkl"))

    return jsonify({
        'initialized': embeddings_exist and citation_exist,
        'embeddings_cached': embeddings_exist,
        'citations_cached': citation_exist
    })


@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the recommender system."""
    global recommender, is_initialized

    try:
        data = request.json or {}
        force = data.get('force', False)
        collection_id = data.get('collection_id', None)

        # Set collection ID in environment if provided
        if collection_id:
            os.environ['ZOTERO_COLLECTION_ID'] = collection_id

        recommender = PaperRecommender()
        recommender.initialize(force_rebuild=force)
        is_initialized = True

        return jsonify({
            'success': True,
            'message': 'Recommendation engine initialized successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recommend', methods=['POST'])
def get_recommendations():
    """Get paper recommendations."""
    global recommender, is_initialized

    try:
        # Parse request
        data = request.json or {}

        # Get default weights from config
        rec_config = config_manager.get_recommendation_config()
        default_citation = rec_config.get('citation_weight', 0.3)
        default_similarity = rec_config.get('similarity_weight', 0.7)

        days_back = data.get('days', 7)
        top_n = data.get('top', 10)
        citation_weight = data.get('citation_weight', default_citation)
        similarity_weight = data.get('similarity_weight', default_similarity)
        use_journal_filter = data.get('use_journal_filter', True)
        custom_journals = data.get('journals', None)
        collection_id = data.get('collection_id', None)

        # Set collection ID in environment if provided
        if collection_id:
            os.environ['ZOTERO_COLLECTION_ID'] = collection_id

        # Ensure recommender exists and matches the requested collection
        if recommender is None:
            recommender = PaperRecommender()
            is_initialized = False

        # Compute per-collection cache paths
        cache_dir = ".cache"
        raw_collection = os.getenv('ZOTERO_COLLECTION_ID') or 'all'
        collection_key = (''.join(c if c.isalnum() else '_' for c in raw_collection.lower()).strip('_') or 'all')
        emb_path = os.path.join(cache_dir, f"library_embeddings_{collection_key}.pkl")
        cit_path = os.path.join(cache_dir, f"citation_network_{collection_key}.pkl")

        # Lazy-load from per-collection cache if needed
        if not is_initialized:
            if not os.path.exists(emb_path):
                return jsonify({
                    'success': False,
                    'error': 'System not initialized for this collection. Please initialize first.'
                }), 400

            # Load from cache (engines will read per-collection files)
            recommender.library_papers = recommender.zotero.fetch_library()
            recommender.similarity.build_library_profile(recommender.library_papers)
            recommender.citation_scorer.build_library_network(
                recommender.openalex,
                recommender.library_papers
            )
            recommender.is_initialized = True
            is_initialized = True

        # Get recommendations
        recommendations = recommender.get_recommendations(
            days_back=days_back,
            limit=top_n,
            citation_weight=citation_weight,
            similarity_weight=similarity_weight,
            use_journal_filter=use_journal_filter,
            custom_journals=custom_journals
        )

        # Save search results to server-side cache
        cache_dir = ".cache"
        os.makedirs(cache_dir, exist_ok=True)
        search_cache_file = os.path.join(cache_dir, "last_search_results.json")
        try:
            with open(search_cache_file, 'w') as f:
                json.dump({
                    'params': {
                        'days': days_back,
                        'top': top_n,
                        'citation_weight': citation_weight,
                        'similarity_weight': similarity_weight,
                        'use_journal_filter': use_journal_filter,
                        'custom_journals': custom_journals,
                        'collection_id': collection_id
                    },
                    'results': recommendations
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save search results to cache: {e}")

        return jsonify({
            'success': True,
            'count': len(recommendations),
            'recommendations': recommendations
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/journals/default', methods=['GET'])
def get_default_journals():
    """Get the default journal list."""
    return jsonify({
        'journals': TOP_BIOLOGY_MEDICINE_JOURNALS
    })


@app.route('/api/journals/library', methods=['GET'])
def get_library_journals():
    """Get journals from user's library."""
    global recommender

    try:
        if recommender is None or not recommender.library_papers:
            recommender_temp = PaperRecommender()
            recommender_temp.library_papers = recommender_temp.zotero.fetch_library()
        else:
            recommender_temp = recommender

        journals = recommender_temp.get_top_journals(top_n=50)

        return jsonify({
            'journals': journals
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/collections', methods=['GET'])
def get_collections():
    """List all Zotero collections."""
    try:
        from src.zotero_client import ZoteroClient

        zotero_client = ZoteroClient()
        collections = zotero_client.list_collections()

        return jsonify({
            'success': True,
            'collections': collections
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reviewed/mark', methods=['POST'])
def mark_paper_reviewed():
    """Mark a paper as reviewed."""
    try:
        data = request.json or {}
        paper_id = data.get('paper_id')
        paper_data = data.get('paper_data', {})

        if not paper_id:
            return jsonify({
                'success': False,
                'error': 'Paper ID is required'
            }), 400

        reviewed_manager.mark_as_reviewed(paper_id, paper_data)

        return jsonify({
            'success': True,
            'message': 'Paper marked as reviewed'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reviewed/list', methods=['GET'])
def get_reviewed_papers():
    """Get all reviewed papers."""
    try:
        reviewed_papers = reviewed_manager.get_all_reviewed()

        return jsonify({
            'success': True,
            'count': len(reviewed_papers),
            'papers': reviewed_papers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reviewed/check/<paper_id>', methods=['GET'])
def check_reviewed_status(paper_id):
    """Check if a paper is reviewed."""
    try:
        is_reviewed = reviewed_manager.is_reviewed(paper_id)

        return jsonify({
            'success': True,
            'is_reviewed': is_reviewed
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reviewed/clear', methods=['POST'])
def clear_reviewed_papers():
    """Clear all reviewed papers."""
    try:
        reviewed_manager.clear_all()

        return jsonify({
            'success': True,
            'message': 'All reviewed papers cleared'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search-cache/clear', methods=['POST'])
def clear_search_cache():
    """Clear the cached search results."""
    try:
        cache_dir = ".cache"
        search_cache_file = os.path.join(cache_dir, "last_search_results.json")
        
        if os.path.exists(search_cache_file):
            os.remove(search_cache_file)
            return jsonify({
                'success': True,
                'message': 'Search results cache cleared'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No search cache found to clear'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/email/send', methods=['POST'])
def send_results_email():
    """Send search results via email."""
    try:
        data = request.json or {}
        to_email = data.get('email')
        results = data.get('results')
        search_params = data.get('search_params', {})

        if not to_email:
            return jsonify({
                'success': False,
                'error': 'Email address is required'
            }), 400

        if not results:
            return jsonify({
                'success': False,
                'error': 'No results to send. Please run a search first.'
            }), 400

        # Check if email is configured
        if not email_sender.is_configured():
            return jsonify({
                'success': False,
                'error': 'Email not configured. Please set SMTP_USERNAME and SMTP_PASSWORD in .env file.'
            }), 500

        # Send email
        email_sender.send_search_results(to_email, results, search_params)

        return jsonify({
            'success': True,
            'message': f'Search results sent to {to_email}'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to send email: {str(e)}'
        }), 500


@app.route('/api/email/configured', methods=['GET'])
def check_email_configured():
    """Check if email is configured."""
    return jsonify({
        'configured': email_sender.is_configured()
    })


@app.route('/api/quit', methods=['POST'])
def quit_app():
    """Shut down the application."""
    def shutdown():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=shutdown, daemon=True).start()
    return jsonify({'success': True, 'message': 'Shutting down...'})


def open_browser():
    """Open the browser after a short delay to ensure server is ready."""
    time.sleep(1.5)  # Wait for server to start
    webbrowser.open('http://127.0.0.1:5000/')


if __name__ == '__main__':
    # Only open browser in the actual server process, not in the reloader parent process
    # WERKZEUG_RUN_MAIN is 'true' only in the reloader child process (where server runs in debug mode)
    # In non-debug mode, WERKZEUG_RUN_MAIN is not set, so we check for both cases
    import os
    debug_mode = True  # Set to True for debug mode
    if not debug_mode or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        # This is either:
        # - Non-debug mode (WERKZEUG_RUN_MAIN not set, but debug=False so we're in main process)
        # - Debug mode reloader child (WERKZEUG_RUN_MAIN='true', this is where server runs)
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    # If debug_mode=True and WERKZEUG_RUN_MAIN is not set, we're in the parent process that spawns reloader - skip
    
    app.run(debug=debug_mode, port=5000)
