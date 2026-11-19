import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from scheduler.models import (
    ScheduledPost, InstagramAccount, YouTubeAccount,
    LinkedInAccount, RedditAccount, SnapchatAccount, UserSubscription,
    UserProfile, Workspace, WorkspaceMember
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

    def test_workspace_creation_and_member_role_assignment(self):
        """Test workspace management, inviting team members, and role assignment."""
        # 1. Setup subscription with member capacity to test role assignments
        sub, _ = UserSubscription.objects.get_or_create(user=self.user)
        sub.plan = 'CREATOR'
        sub.members_per_workspace_limit = 5
        sub.save()

        # 2. Create colleague users to invite
        colleague_admin = User.objects.create_user(
            username='admin_colleague',
            email='colleague_admin@example.com',
            password='password123'
        )
        colleague_editor = User.objects.create_user(
            username='editor_colleague',
            email='colleague_editor@example.com',
            password='password123'
        )

        # 3. Get settings page (triggers auto-creation of personal workspace via context processor)
        resp = self.client.get('/settings/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Team Members &amp; Role Permissions")
        
        ws = Workspace.objects.filter(owner=self.user).first()
        self.assertIsNotNone(ws)
        self.assertEqual(ws.get_user_role(self.user), 'OWNER')
        self.assertTrue(ws.is_admin_or_owner(self.user))
        self.assertTrue(ws.can_manage_content(self.user))

        # 3. Owner adds a colleague with ADMIN role
        add_admin_resp = self.client.post('/settings/', {
            'action': 'add_member',
            'username_or_email': 'colleague_admin@example.com',
            'role': 'ADMIN',
        })
        self.assertEqual(add_admin_resp.status_code, 302)
        self.assertTrue(ws.memberships.filter(user=colleague_admin, role='ADMIN').exists())
        self.assertTrue(ws.is_admin_or_owner(colleague_admin))

        # 4. Owner adds another colleague with VIEWER role
        add_editor_resp = self.client.post('/settings/', {
            'action': 'add_member',
            'username_or_email': 'editor_colleague',
            'role': 'VIEWER',
        })
        self.assertEqual(add_editor_resp.status_code, 302)
        member_rec = ws.memberships.get(user=colleague_editor)
        self.assertEqual(member_rec.role, 'VIEWER')
        self.assertFalse(ws.can_manage_content(colleague_editor))

        # 5. Update role from VIEWER to EDITOR
        update_role_resp = self.client.post('/settings/', {
            'action': 'update_member_role',
            'member_id': member_rec.id,
            'role': 'EDITOR',
        })
        self.assertEqual(update_role_resp.status_code, 302)
        member_rec.refresh_from_db()
        self.assertEqual(member_rec.role, 'EDITOR')
        self.assertTrue(ws.can_manage_content(colleague_editor))

        # 6. Switch workspace test
        new_ws = Workspace.objects.create(name="Second Team", owner=self.user)
        switch_resp = self.client.get(f'/workspace/switch/{new_ws.id}/')
        self.assertEqual(switch_resp.status_code, 302)
        self.assertEqual(self.client.session.get('active_workspace_id'), new_ws.id)

    def test_workspace_and_member_plan_limits(self):
        """Test strict plan-based enforcement of workspace limits and team member limits."""
        # 1. Start with Free plan (1 workspace max, 2 members per workspace max)
        sub, _ = UserSubscription.objects.get_or_create(user=self.user)
        sub.plan = 'FREE'
        sub.workspaces_limit = 1
        sub.members_per_workspace_limit = 2
        sub.save()

        # Trigger settings GET to ensure default workspace exists
        resp = self.client.get('/settings/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['workspace_limit'], 1)
        self.assertEqual(resp.context['member_limit'], 2)
        self.assertEqual(Workspace.objects.filter(owner=self.user).count(), 1)

        # 2. Free user attempts to create a 2nd workspace -> BLOCKED
        create_resp = self.client.post('/settings/', {
            'action': 'create_workspace',
            'name': 'Second Unauthorized Workspace',
            'timezone': 'Asia/Kolkata',
        }, follow=True)
        self.assertEqual(create_resp.status_code, 200)
        self.assertEqual(Workspace.objects.filter(owner=self.user).count(), 1)
        messages_text = [m.message for m in create_resp.context['messages']]
        self.assertTrue(any('Workspace limit reached' in m for m in messages_text))

        # 3. Add 1 team member to reach max members limit (Owner + 1 member = 2 members)
        u2 = User.objects.create_user(username='member_one', email='m1@test.com', password='pw')
        add_resp = self.client.post('/settings/', {
            'action': 'add_member',
            'username_or_email': 'member_one',
            'role': 'EDITOR',
        }, follow=True)
        self.assertEqual(add_resp.status_code, 200)
        ws = Workspace.objects.filter(owner=self.user).first()
        self.assertEqual(ws.memberships.count(), 2) # Owner + 1 member

        # 4. Attempt to add a 3rd member (exceeding limit of 2) -> BLOCKED
        u3 = User.objects.create_user(username='member_two', email='m2@test.com', password='pw')
        add_blocked_resp = self.client.post('/settings/', {
            'action': 'add_member',
            'username_or_email': 'member_two',
            'role': 'VIEWER',
        }, follow=True)
        self.assertEqual(add_blocked_resp.status_code, 200)
        self.assertEqual(ws.memberships.count(), 2) # Still 2, not 3
        messages_text = [m.message for m in add_blocked_resp.context['messages']]
        self.assertTrue(any('Team member limit reached' in m for m in messages_text))

        # 5. Upgrade user to CREATOR / Marketer plan (3 workspaces, 5 members)
        sub.plan = 'CREATOR'
        sub.workspaces_limit = 3
        sub.members_per_workspace_limit = 5
        sub.save()

        # 6. Now create 2nd workspace -> ALLOWED
        create_ok_resp = self.client.post('/settings/', {
            'action': 'create_workspace',
            'name': 'Client 2 Growth Studio',
            'timezone': 'Asia/Kolkata',
        }, follow=True)
        self.assertEqual(create_ok_resp.status_code, 200)
        self.assertEqual(Workspace.objects.filter(owner=self.user).count(), 2)

        # Switch active session back to the first workspace to test adding member to it
        self.client.get(f'/workspace/switch/{ws.id}/')

        # 7. Add member_two to the first workspace -> ALLOWED now that limit is 5
        add_ok_resp = self.client.post('/settings/', {
            'action': 'add_member',
            'username_or_email': 'member_two',
            'role': 'VIEWER',
        }, follow=True)
        self.assertEqual(add_ok_resp.status_code, 200)
        self.assertEqual(ws.memberships.count(), 3)





