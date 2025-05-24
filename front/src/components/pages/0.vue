<template>
  <div class="page-container">
    <v-scale-transition>
      <div class="header-section">
        <v-icon size="40" color="primary" class="pulse-icon">mdi-clipboard-check</v-icon>
        <h2 class="text-h4 gradient-text">Research Participant Consent Form</h2>
      </div>
    </v-scale-transition>

    <v-container class="content-grid">
      <v-row>
        <v-col cols="12">
          <v-card class="consent-card">
            <v-card-text>
              <h3 class="text-h5 mb-4">Project Title: Information Dissemination in Electronic Financial Markets</h3>
              
              <p><strong>Institution:</strong> Royal Holloway, University of London -- Department of Economics</p>
              <p><strong>Researchers:</strong> Prof. Alessio Sancetta, Prof. Francesco Feri, Prof. Michael Naef, Dr. Wenbin Wei, Dr. Mariol Jonuzaj</p>
              <p><strong>Funding Body:</strong> The Leverhulme Trust</p>
              
              <h4 class="text-h6 mt-4">Introduction</h4>
              <p>Royal Holloway, University of London supports the practise of protecting human participants in research. This form provides you with important information about taking part in this study. Your participation in this study is entirely voluntary, and you have the right to withdraw at any time without penalty or negative consequences. If you choose to withdraw, any data collected from you will be deleted and not included in the final analysis.</p>
              
              <h4 class="text-h6 mt-4">Summary</h4>
              <p>The purpose of this study is to investigate the interaction between human and machines (AI agents) in electronic financial markets. In this study, we will ask you to participate in various experimental financial markets where you will be able to make decisions regarding buying or selling a virtual financial asset (not a real asset). This study will take approximately 30 minutes to complete. Taking part in this study is a great opportunity to learn how electronic financial markets operate, and you will also have the chance to earn financial profits depending on your performance.</p>
              
              <h4 class="text-h6 mt-4">Ethical Approval</h4>
              <p>This study has received ethics approval from Royal Holloway, University of Lonon's Research Ethics Committee, with the approval ID of [????].</p>
              
              <h4 class="text-h6 mt-4">Data collection</h4>
              <p>During this study, we will collect data from you only related to your buy or sell decision orders. At the end of the study, you will be asked to complete a short survey about your overall experience with our platform. Additionally, the Prolific platform will provide some basic demographic characteristics such as age, gender and education. All data will be anonymized and labelled using only your Unique Prolific ID.</p>
              
              <h4 class="text-h6 mt-4">Data Protection</h4>
              <p>This research commits to abide by the Data Protection Act (2018).</p>
              
              <h4 class="text-h6 mt-4">General Data Protection Regulation Statement</h4>
              <p>Important General Data Protection Regulation information (GDPR). Royal Holloway, University of London is the sponsor for this study and is based in the UK. We will be using information from you in order to undertake this study and will act as the data controller for this study. This means that we are responsible for looking after your information and using it properly. Any data you provide during the completion of the study will be stored securely on hosted on servers within the European Economic Area'. Royal Holloway is designated as a public authority and in accordance with the Royal Holloway and Bedford New College Act 1985 and the Statutes which govern the College, we conduct research for the public benefit and in the public interest. Royal Holloway has put in place appropriate technical and organisational security measures to prevent your personal data from being accidentally lost, used or accessed in any unauthorised way or altered or disclosed. Royal Holloway has also put in place procedures to deal with any suspected personal data security breach and will notify you and any applicable regulator of a suspected breach where legally required to do so. To safeguard your rights, we will use the minimum personally-identifiable information possible (i.e., the email address you provide us). The lead researcher will keep your contact details confidential and will use this information only as required (i.e., to provide a summary of the study results if requested and/or for the prize draw). The lead researcher will keep information about you and data gathered from the study, the duration of which will depend on the study. Certain individuals from RHUL may look at your research records to check the accuracy of the research study. If the study is published in a relevant peer-reviewed journal, the anonymised data may be made available to third parties. The people who analyse the information will not be able to identify you. You can find out more about your rights under the GDPR and Data Protection Act 2018 by visiting <a href="https://www.royalholloway.ac.uk/about-us/more/governance-and-strategy/data-protection/" target="_blank">https://www.royalholloway.ac.uk/about-us/more/governance-and-strategy/data-protection/</a> and if you wish to exercise your rights, please contact <a href="mailto:dataprotection@royalholloway.ac.uk">dataprotection@royalholloway.ac.uk</a></p>
              
              <h4 class="text-h6 mt-4">Compensation</h4>
              <p>For your time and effort, you will receive compensation through the Prolific platform payment. You will receive a participation fee of £5 GBP, and additional compensation will be provided based on your performance. This is subject to completing the entire study and submitting the completion code displayed at the end of the study to the prolific platform.</p>
              
              <h4 class="text-h6 mt-4">Contact information</h4>
              <p>If you have any question, concerns, or feedback related to this study, please feel free to contact us through the Prolific message box.</p>
              
              <h4 class="text-h6 mt-4">Statement of consent</h4>
              <p>I confirm that:</p>
              <ul>
                <li>I have read and understood the information provided in this consent form.</li>
                <li>I have had the opportunity to ask questions and have received satisfactory answers.</li>
                <li>I voluntarily agree to participate in the study "Information Dissemination in Electronic Financial Markets"</li>
                <li>I understand that I can withdraw from the study at any time without penalty or negative consequences.</li>
              </ul>
              
              <v-checkbox
                v-model="consentGiven"
                label="I consent to participate"
                color="primary"
                class="mt-4"
                @update:model-value="updateConsent"
              ></v-checkbox>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <div class="text-center mt-6">
      <v-btn
        color="primary"
        size="large"
        :disabled="!consentGiven"
        @click="submitConsent"
        class="consent-button"
      >
        Continue
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, defineEmits } from 'vue';
import { useRouter } from 'vue-router';
import { useTraderStore } from "@/store/app";
import { useAuthStore } from "@/store/auth";
import axios from '@/api/axios';

const router = useRouter();
const traderStore = useTraderStore();
const authStore = useAuthStore();
const consentGiven = ref(false);

const emit = defineEmits(['update:canProgress']);

const updateConsent = (value) => {
  emit('update:canProgress', value);
};

const submitConsent = async () => {
  if (!consentGiven.value) return;

  try {
    // Get user information
    const traderId = traderStore.traderId;
    const marketId = traderStore.marketId;
    const traderUuid = traderStore.traderId;
    
    console.log('Trader info:', { traderId, marketId, traderUuid });
    console.log('Auth store state:', { 
      isAuthenticated: authStore.isAuthenticated,
      user: authStore.user,
      prolificId: authStore.prolificId
    });
    
    // Check if user is from Prolific
    const isProlificUser = !!authStore.prolificId;
    
    // Get user ID based on user type
    let userId = '';
    let userType = '';
    
    if (isProlificUser) {
      userId = authStore.prolificId;
      userType = 'prolific';
    } else if (authStore.user?.email) {
      // Extract Gmail username (part before @)
      const email = authStore.user.email;
      userId = email.split('@')[0];
      userType = 'google';
    } else if (authStore.user?.uid) {
      // Fallback to UID if email is not available
      userId = authStore.user.uid;
      userType = 'google';
    }
    
    console.log('User identification:', { userId, userType, isProlificUser });
    
    // First try the debug endpoint to see if we can communicate with the backend
    try {
      const requestData = {
        trader_id: traderId,
        user_id: userId || '',
        user_type: userType || '',
        prolific_id: authStore.prolificId || '',
        consent_given: true
      };
      
      console.log('Trying debug endpoint first:', requestData);
      const debugResponse = await axios.post('/consent/debug', requestData);
      console.log('Debug endpoint response:', debugResponse.data);
      
      // Now try the actual consent save endpoint
      console.log('Sending consent data to backend:', requestData);
      const response = await axios.post('/consent/save', requestData);
      console.log(`Consent data saved for user:`, response.data);
    } catch (submitError) {
      console.error('Error submitting consent:', submitError);
      if (submitError.response) {
        console.error('Response data:', submitError.response.data);
        console.error('Response status:', submitError.response.status);
        console.error('Response headers:', submitError.response.headers);
      }
      // Continue with navigation even if consent saving fails
    }
    
    // Navigate to the next page
    router.push(`/onboarding/${marketId}/${traderUuid}/welcome`);
  } catch (error) {
    console.error('Error handling consent:', error);
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
      console.error('Response headers:', error.response.headers);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Request error:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error message:', error.message);
    }
  }
};
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.header-section {
  text-align: center;
  margin-bottom: 2rem;
}

.gradient-text {
  background: linear-gradient(45deg, #2196F3, #4CAF50);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: bold;
  margin: 1rem 0;
}

.pulse-icon {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); }
}

.consent-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  max-height: 60vh;
  overflow-y: auto;
}

.consent-button {
  min-width: 150px;
}

@media (max-width: 960px) {
  .page-container {
    padding: 1rem;
  }
}
</style>
