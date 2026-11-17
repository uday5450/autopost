import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from scheduler.models import (
    ScheduledPost, InstagramAccount, YouTubeAccount,
    LinkedInAccount, RedditAccount, SnapchatAccount, UserSubscription,
    UserProfile
)

class PostBridgeFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test@example.com', email='test@example.com', password='password123')
        self.client.login(username='test@example.com', password='password123')
        
        # Create test accounts
        self.ig = InstagramAccount.objects.create(
            user=self.user, name="Brand IG", instagram_user_id="12345",
            access_token="tok_123", is_active=True
        )
        self.yt = YouTubeAccount.objects.create(
            user=self.user, name="Brand YT", channel_id="UC12345",
            access_token="tok_yt", is_active=True
        )
        self.li = LinkedInAccount.objects.create(
            user=self.user, name="Brand LinkedIn", urn_id="urn:li:person:123",
            access_token="tok_li", is_active=True
        )

    def test_create_multi_platform_posts(self):
        """Test scheduling posts with per-platform custom captions."""
        post_time = (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post('/posts/create/', {
            'ig_accounts': [self.ig.pk],
            'yt_accounts': [self.yt.pk],
            'li_accounts': [self.li.pk],
            'post_type': 'IMAGE',
            'title': 'Universal Title',
            'caption': 'Universal Caption #all',
            'caption_ig': 'IG Custom Caption #instagram',
            'caption_yt': 'YT Custom Description',
            'title_yt': 'Specific Video Title',
            'caption_li': 'LinkedIn Professional Insight',
            'scheduled_time': post_time,
            'media_url': 'https://example.com/image.jpg',
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify 3 posts were created
        self.assertEqual(ScheduledPost.objects.count(), 3)
        
        # Verify IG post has IG caption
        ig_post = ScheduledPost.objects.get(platform='INSTAGRAM')
        self.assertEqual(ig_post.caption, 'IG Custom Caption #instagram')

        # Verify YT post has YT title
        yt_post = ScheduledPost.objects.get(platform='YOUTUBE')
        self.assertEqual(yt_post.title, 'Specific Video Title')

    def test_calendar_events_api(self):
        """Test that the calendar API returns events properly formatted for FullCalendar."""
        ScheduledPost.objects.create(
            user=self.user, platform='INSTAGRAM', account=self.ig,
            caption='Test Calendar Post', scheduled_time=timezone.now()
        )
        response = self.client.get('/api/calendar/events/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertIn('[Instagram]', data[0]['title'])

    def test_razorpay_order_and_verify(self):
        """Test Razorpay order creation and payment verification."""
        # 1. Create order
        resp = self.client.post('/pricing/create-order/', {'plan': 'CREATOR'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['plan'], 'CREATOR')

        # 2. Verify payment
        v_resp = self.client.post('/pricing/verify/', {
            'razorpay_payment_id': 'pay_test123',
            'razorpay_order_id': data['order_id'],
            'razorpay_signature': 'sig_test123',
            'plan': 'CREATOR',
        })
        self.assertEqual(v_resp.status_code, 200)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertEqual(sub.plan, 'CREATOR')
        self.assertTrue(sub.is_active)

    def test_developer_rest_api_create_post(self):
        """Test AI agent / MCP REST API programmatic post creation."""
        resp = self.client.post('/api/v1/posts/create/', {
            'platform': 'INSTAGRAM',
            'caption': 'AI agent scheduled post',
            'media_url': 'https://example.com/photo.jpg',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(ScheduledPost.objects.filter(caption='AI agent scheduled post').count(), 1)

    def test_seo_robots_and_sitemap(self):
        """Test that robots.txt and sitemap.xml return 200 with appropriate crawl directives."""
        # robots.txt
        robots_resp = self.client.get('/robots.txt')
        self.assertEqual(robots_resp.status_code, 200)
        self.assertIn('User-agent: *', robots_resp.content.decode('utf-8'))
        self.assertIn('Sitemap:', robots_resp.content.decode('utf-8'))

        # sitemap.xml
        sitemap_resp = self.client.get('/sitemap.xml')
        self.assertEqual(sitemap_resp.status_code, 200)
        content = sitemap_resp.content.decode('utf-8')
        self.assertIn('<urlset', content)
        self.assertIn('/pricing/', content)

        # landing page Schema.org JSON-LD (tested with unauthenticated guest/crawler)
        anon_client = Client()
        landing_resp = anon_client.get('/')
        self.assertEqual(landing_resp.status_code, 200)
        landing_content = landing_resp.content.decode('utf-8')
        self.assertIn('FeedBridge', landing_content)
        self.assertIn('SoftwareApplication', landing_content)

    def test_dynamic_pricing_and_coupon(self):
        """Test coupon validation and dynamic custom accounts price calculation."""
        from scheduler.models import PricingPlan, DiscountCoupon
        plan, _ = PricingPlan.objects.get_or_create(
            plan_code='TEST_PRO', defaults={
                'name': 'Test Plan', 'price_inr': 2000,
                'max_connected_accounts': 2, 'price_per_additional_account': 200,
                'is_active': True
            }
        )
        coupon, _ = DiscountCoupon.objects.get_or_create(
            code='TEST50', defaults={'discount_percent': 50, 'is_active': True}
        )

        # 1. Test coupon validation API
        resp = self.client.post('/pricing/validate-coupon/', {
            'code': 'TEST50', 'plan': 'TEST_PRO', 'custom_accounts': 2
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['discount_inr'], 1000) # 50% of 2000 = 1000
        self.assertEqual(data['final_price_inr'], 1000)

        # 2. Test order creation with custom accounts (4 accounts = 2000 + 2*200 = 2400 - 50% = 1200)
        order_resp = self.client.post('/pricing/create-order/', {
            'plan': 'TEST_PRO', 'custom_accounts': 4, 'coupon': 'TEST50'
        }, content_type='application/json')
        self.assertEqual(order_resp.status_code, 200)
        order_data = order_resp.json()
        self.assertTrue(order_data['success'])
        self.assertEqual(order_data['price_inr'], 1200)
        self.assertEqual(order_data['amount'], 120000) # In paise

        # 3. Test yearly billing cycle order (plan 2000 x 12 = 24000 - 20% yearly = 19200)
        yearly_resp = self.client.post('/pricing/create-order/', {
            'plan': 'TEST_PRO', 'billing_cycle': 'yearly'
        }, content_type='application/json')
        self.assertEqual(yearly_resp.status_code, 200)
        y_data = yearly_resp.json()
        self.assertEqual(y_data['billing_cycle'], 'yearly')
        self.assertEqual(y_data['price_inr'], 19200)
        self.assertEqual(y_data['amount'], 1920000)


    def test_growth_guide_and_mcp_endpoint(self):
        """Test Growth Guide knowledge hub and MCP JSON-RPC protocol endpoint."""
        # 1. Growth guide view
        guide_resp = self.client.get('/growth-guide/')
        self.assertEqual(guide_resp.status_code, 200)
        self.assertIn('Growth Guide', guide_resp.content.decode('utf-8'))

        # 2. MCP JSON-RPC tools/list
        api_key = f"pb_live_{self.user.id}_{self.user.username}_sec"
        mcp_resp = self.client.post(
            '/api/mcp/',
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {api_key}'
        )
        self.assertEqual(mcp_resp.status_code, 200)
        data = mcp_resp.json()
        self.assertIn('result', data)
        tool_names = [t['name'] for t in data['result']['tools']]
        self.assertIn('feedbridge_schedule_post', tool_names)
        self.assertIn('feedbridge_get_accounts', tool_names)

        # 3. MCP JSON-RPC tools/call (Schedule post)
        call_resp = self.client.post(
            '/api/mcp/',
            data=json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "feedbridge_schedule_post",
                    "arguments": {
                        "platform": "INSTAGRAM",
                        "caption": "Scheduled by MCP coding agent!"
                    }
                }
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {api_key}'
        )
        self.assertEqual(call_resp.status_code, 200)
        call_data = call_resp.json()
        self.assertIn('result', call_data)
        self.assertTrue(ScheduledPost.objects.filter(caption='Scheduled by MCP coding agent!').exists())

    def test_signup_privacy_policy_and_login(self):
        """Test signup requires terms & privacy policy agreement, and test login and onboarding workflow."""
        anon = Client()

        # 1. Signup without terms agreement must fail
        resp_fail = anon.post('/accounts/signup/', {
            'full_name': 'Test User',
            'phone_number': '9876543210',
            'email': 'newuser@test.com',
            'password': 'password123',
            'password_confirm': 'password123'
        })
        self.assertEqual(resp_fail.status_code, 200)
        self.assertFalse(User.objects.filter(email='newuser@test.com').exists())

        # 2. Signup with terms_agreed, name, country, and phone must succeed and redirect to onboarding_connect (not dashboard)
        resp_success = anon.post('/accounts/signup/', {
            'full_name': 'Test User',
            'phone_number': '9876543210',
            'country_code': '+91',
            'country_name': 'India',
            'email': 'newuser@test.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'terms_agreed': 'true'
        })
        self.assertEqual(resp_success.status_code, 302)
        self.assertIn('/onboarding/connect/', resp_success.url)
        self.assertTrue(User.objects.filter(email='newuser@test.com').exists())
        profile = UserProfile.objects.get(user__email='newuser@test.com')
        self.assertEqual(profile.full_name, 'Test User')
        self.assertEqual(profile.phone_number, '9876543210')
        self.assertEqual(profile.country_code, '+91')

        # 3. Test Onboarding Connect Page renders channels
        onboarding_resp = anon.get('/onboarding/connect/')
        self.assertEqual(onboarding_resp.status_code, 200)
        self.assertContains(onboarding_resp, 'Instagram')
        self.assertContains(onboarding_resp, 'YouTube')
        self.assertContains(onboarding_resp, 'TikTok')

        # 4. Quick connect a channel via onboarding page
        connect_post = anon.post('/onboarding/connect/', {
            'action': 'quick_connect',
            'platform': 'instagram'
        })
        self.assertEqual(connect_post.status_code, 302)
        self.assertTrue(InstagramAccount.objects.filter(user__email='newuser@test.com').exists())

        # 5. Complete onboarding to proceed to dashboard
        complete_post = anon.post('/onboarding/connect/', {
            'action': 'complete_onboarding'
        })
        self.assertEqual(complete_post.status_code, 302)
        self.assertEqual(complete_post.url, '/dashboard/')
        profile.refresh_from_db()
        self.assertTrue(profile.onboarding_completed)

        # 6. Login with newly created user
        anon2 = Client()
        login_resp = anon2.post('/accounts/login/', {
            'email': 'newuser@test.com',
            'password': 'password123'
        })
        self.assertEqual(login_resp.status_code, 302)
        self.assertEqual(login_resp.url, '/dashboard/')



