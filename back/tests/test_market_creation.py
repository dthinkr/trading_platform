"""
Tests for market creation flow - this catches the REAL issues after RabbitMQ removal.
These tests simulate the actual user journey that was causing 500 errors.
"""

import sys
import os
# Add the back directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from core.trader_manager import TraderManager  
from core.data_models import TradingParameters, TraderRole
from api.market_pipeline import MarketPipeline


class TestMarketCreation:
    """Test the actual market creation flow that was breaking"""
    
    @pytest.fixture
    def default_params(self):
        """Default trading parameters"""
        return TradingParameters(
            predefined_goals=[100],  # Single informed trader goal
            num_noise_traders=2,
            num_informed_traders=1,
            trading_day_duration=5,
            initial_cash=10000,
            initial_stocks=50,
            default_price=100,
            # Add missing parameters that trader_manager expects
            order_book_levels=5,
            step=1,
            initial_depth=3
        )
    
    @pytest.mark.asyncio
    async def test_trader_manager_creation(self, default_params):
        """Test that TraderManager can be created without TypeError"""
        try:
            # This was failing with: TypeError: NoiseTrader.__init__() got an unexpected keyword argument 'initial_cash'
            trader_manager = TraderManager(default_params)
            
            # Check that traders were created successfully
            assert len(trader_manager.noise_traders) == default_params.num_noise_traders
            assert len(trader_manager.informed_traders) == default_params.num_informed_traders
            
            # Verify trader IDs are correct
            noise_ids = [trader.id for trader in trader_manager.noise_traders]
            assert "NOISE_0" in noise_ids
            assert "NOISE_1" in noise_ids
            
            informed_ids = [trader.id for trader in trader_manager.informed_traders]
            assert "INFORMED_0" in informed_ids
            
            await trader_manager.cleanup()
            
        except Exception as e:
            pytest.fail(f"TraderManager creation failed: {e}")
    
    @pytest.mark.asyncio 
    async def test_market_pipeline_creation(self, default_params):
        """Test the market pipeline creation that was causing the 500 error"""
        pipeline = MarketPipeline()
        
        try:
            # Set up the pipeline with params
            pipeline.set_session_templates_from_params(default_params)
            
            # Simulate market creation data
            market_data = {
                "market_id": "TEST_MARKET_123",
                "users": [
                    {
                        "username": "testuser",
                        "goal": 100, 
                        "trader_id": "HUMAN_testuser"
                    }
                ]
            }
            
            # This was the call that was failing in the logs
            market_id = await pipeline._create_market_from_data(market_data, default_params)
            
            assert market_id == "TEST_MARKET_123"
            assert market_id in pipeline.markets
            
            # Verify the trader manager was created successfully
            trader_manager = pipeline.markets[market_id]
            assert trader_manager is not None
            assert len(trader_manager.noise_traders) == default_params.num_noise_traders
            
            # Clean up
            await pipeline.cleanup_finished_markets()
            
        except Exception as e:
            pytest.fail(f"Market pipeline creation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_human_trader_addition(self, default_params):
        """Test adding human traders to market"""
        trader_manager = TraderManager(default_params)
        
        try:
            # Add human trader (this should work)
            trader_id = await trader_manager.add_human_trader(
                gmail_username="testuser",
                role=TraderRole.INFORMED,
                goal=100
            )
            
            assert trader_id == "HUMAN_testuser"
            assert len(trader_manager.human_traders) == 1
            
            # Verify trader exists in traders dict
            assert trader_id in trader_manager.traders
            
            trader = trader_manager.get_trader(trader_id)
            assert trader is not None
            assert trader.goal == 100
            assert trader.role == TraderRole.INFORMED
            
            await trader_manager.cleanup()
            
        except Exception as e:
            pytest.fail(f"Human trader addition failed: {e}")
    
    @pytest.mark.asyncio
    async def test_trader_manager_get_trader_method(self, default_params):
        """Test the get_trader method that was being called in trader_info endpoint"""
        trader_manager = TraderManager(default_params)
        
        try:
            # Add a human trader
            trader_id = await trader_manager.add_human_trader(
                gmail_username="venvoooo", 
                role=TraderRole.INFORMED,
                goal=100
            )
            
            # This is the call that was happening in the endpoints
            trader = trader_manager.get_trader(trader_id)
            
            # Should not return None
            assert trader is not None
            assert hasattr(trader, 'goal')
            assert hasattr(trader, 'role')
            assert trader.id == trader_id
            
            await trader_manager.cleanup()
            
        except Exception as e:
            pytest.fail(f"get_trader method failed: {e}")
    
    def test_trader_parameters_compatibility(self, default_params):
        """Test that all trader classes accept the expected parameters"""
        from traders import NoiseTrader, InformedTrader, HumanTrader
        
        params_dict = default_params.model_dump()
        
        # Test NoiseTrader initialization
        try:
            noise_trader = NoiseTrader(id="TEST_NOISE", params=params_dict)
            assert noise_trader.id == "TEST_NOISE"
        except Exception as e:
            pytest.fail(f"NoiseTrader initialization failed: {e}")
        
        # Test InformedTrader initialization  
        try:
            informed_trader = InformedTrader(id="TEST_INFORMED", params=params_dict)
            assert informed_trader.id == "TEST_INFORMED"
        except Exception as e:
            pytest.fail(f"InformedTrader initialization failed: {e}")
        
        # Test HumanTrader initialization
        try:
            human_trader = HumanTrader(
                id="TEST_HUMAN",
                cash=params_dict["initial_cash"],
                shares=params_dict["initial_stocks"], 
                goal=100,
                role=TraderRole.INFORMED,
                trading_market=None,  # Can be None for this test
                params=params_dict,
                gmail_username="testuser"
            )
            assert human_trader.id == "TEST_HUMAN"
        except Exception as e:
            pytest.fail(f"HumanTrader initialization failed: {e}")


@pytest.mark.integration
class TestRealUserFlow:
    """Integration test that simulates the EXACT flow that was causing 500 errors"""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey_simulation(self):
        """Simulate the exact journey: login -> onboarding -> join waiting room -> market creation"""
        
        # Step 1: Create pipeline (like in endpoints.py)
        pipeline = MarketPipeline()
        
        # Step 2: Set up parameters (like in endpoints.py startup)
        params = TradingParameters(predefined_goals=[100])
        pipeline.set_session_templates_from_params(params)
        
        # Step 3: User tries to join waiting room (like in join-waiting-room endpoint)
        try:
            user_profile = pipeline.UserProfile(
                username="venvoooo",
                is_prolific=False,
                joined_at=1750299952.0
            )
            
            # This should trigger market creation
            market_data = await pipeline.try_form_market(user_profile, params)
            
            if market_data:
                # Step 4: Create the market (this was failing)
                market_id = await pipeline._create_market_from_data(market_data, params)
                
                # Step 5: Verify trader manager exists (for trader_info endpoint)
                trader_manager = pipeline.get_trader_manager("HUMAN_venvoooo")
                assert trader_manager is not None
                
                # Step 6: Verify trader exists in manager
                trader = trader_manager.get_trader("HUMAN_venvoooo")
                assert trader is not None
                
                print(f"✅ Market creation successful: {market_id}")
                
                # Cleanup
                await pipeline.reset_all()
                
        except Exception as e:
            pytest.fail(f"Complete user journey failed: {e}")


if __name__ == "__main__":
    print("Run with: pytest back/tests/test_market_creation.py -v")
    print("This tests the ACTUAL market creation issues that cause 500 errors") 